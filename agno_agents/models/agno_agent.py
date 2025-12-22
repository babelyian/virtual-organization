# -*- coding: utf-8 -*-
import os
import re
import signal
import subprocess
import time

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AgnoAgent(models.Model):
    _name = "agno.agent"
    _description = "Agno Agent Configuration"
    _rec_name = "agent_name"
    _inherit = []

    # ------------------------
    # Fields
    # ------------------------
    agent_name = fields.Char("Agent Name", required=True, help="Name of the Agno agent")
    agent_role = fields.Text(
        "Agent Role",
        required=True,
        help="Description of the agent's role and capabilities",
    )
    instructions = fields.Text("Instructions", help="Additional instructions for the agent")

    model_id = fields.Char(
        "Model ID",
        required=True,
        default="qwen3:latest",
        help="AI model identifier (e.g., qwen3:latest)",
    )
    base_url = fields.Char(
        "Base URL",
        required=True,
        default="https://chat.aiahura.com/api/v1",
        help="API base URL for the model",
    )
    api_key_env = fields.Char(
        "API Key Environment Variable",
        default="API_KEY",
        help="Environment variable name containing the API key",
    )

    add_history_to_context = fields.Boolean("Add History to Context", default=True)
    add_datetime_to_context = fields.Boolean("Add Datetime to Context", default=False)
    markdown = fields.Boolean("Enable Markdown", default=True)
    debug_mode = fields.Boolean("Debug Mode", default=False)
    num_history_runs = fields.Integer("Number of History Runs", default=5)

    db_file = fields.Char("Database File", default="agent.db", help="SQLite database file name")

    is_active = fields.Boolean("Active", default=False)
    status = fields.Selection(
        [
            ("stopped", "Stopped"),
            ("starting", "Starting"),
            ("running", "Running"),
            ("stopping", "Stopping"),
            ("error", "Error"),
        ],
        default="stopped",
        string="Status",
    )

    port = fields.Integer("Port", default=7777, help="Port where agent will be accessible")
    host = fields.Char("Host", default="0.0.0.0", help="Host address")

    error_message = fields.Text("Error Message", readonly=True)
    last_started = fields.Datetime("Last Started", readonly=True)
    last_stopped = fields.Datetime("Last Stopped", readonly=True)

    process_pid = fields.Integer("Process PID", readonly=True)

    # Optional: if you want to keep script path for debugging
    # script_path = fields.Char("Script Path", readonly=True)

    # ------------------------
    # Constraints
    # ------------------------
    @api.constrains("agent_name")
    def _check_agent_name(self):
        for record in self:
            if not record.agent_name or not record.agent_name.strip():
                raise ValidationError(_("Agent name cannot be empty"))

    @api.constrains("port")
    def _check_port(self):
        for record in self:
            if record.port < 1 or record.port > 65535:
                raise ValidationError(_("Port must be between 1 and 65535"))

    # ------------------------
    # Process/Port helpers
    # ------------------------
    def _ss_available(self) -> bool:
        try:
            subprocess.run(["ss", "-h"], capture_output=True, text=True, check=False)
            return True
        except FileNotFoundError:
            return False

    def _get_listening_pids(self, port: int):
        """
        Return a set of PIDs that are LISTENing on TCP port using `ss`.
        ss output contains fragments like: users:(("python",pid=1234,fd=3))
        """
        if not self._ss_available():
            raise UserError(
                _(
                    "Command 'ss' not found. Install iproute2: "
                    "sudo apt-get update && sudo apt-get install -y iproute2"
                )
            )

        r = subprocess.run(
            ["ss", "-H", "-lptn", f"sport = :{int(port)}"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        return set(int(m.group(1)) for m in re.finditer(r"pid=(\d+)", out))

    def _port_is_listening(self, port: int) -> bool:
        try:
            return bool(self._get_listening_pids(port))
        except Exception:
            # If we cannot determine, be conservative (assume might be listening)
            return True

    def _kill_pids(self, pids, sig):
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
            except PermissionError as e:
                raise UserError(_(f"No permission to kill pid {pid}: {e}"))

    def _kill_by_port(self, port: int, term_wait: float = 2.0) -> bool:
        """
        Kill whatever is listening on `port`. SIGTERM -> wait -> SIGKILL if still listening.
        Returns True if we found any pids to kill.
        """
        pids = self._get_listening_pids(port)
        if not pids:
            return False

        self._kill_pids(pids, signal.SIGTERM)
        time.sleep(term_wait)

        pids_after = self._get_listening_pids(port)
        if pids_after:
            self._kill_pids(pids_after, signal.SIGKILL)

        return True

    def _kill_process_group(self, pid: int, term_wait: float = 2.0) -> bool:
        """
        Try to kill the process group of a PID.
        Returns True if we attempted to kill a group, False if PID didn't exist.
        """
        try:
            pgid = os.getpgid(pid)
        except ProcessLookupError:
            return False

        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            return False
        except PermissionError as e:
            raise UserError(_(f"No permission to stop agent process group: {e}"))

        time.sleep(term_wait)

        # If still exists, SIGKILL
        try:
            os.killpg(pgid, 0)
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError as e:
            raise UserError(_(f"No permission to SIGKILL agent process group: {e}"))

        return True

    # ------------------------
    # Actions
    # ------------------------
    def action_start_agent(self):
        """Start the Agno agent"""
        self.ensure_one()

        if self.is_active:
            raise UserError(_("Agent is already active"))

        # If port is already taken, fail early (prevents "running" state while another process owns port)
        if self._ss_available():
            if self._port_is_listening(self.port):
                raise UserError(_(f"Port {self.port} is already in use. Stop the process using it or change the port."))

        try:
            self.status = "starting"
            self.error_message = False

            script_content = self._generate_agent_script()
            script_path = f"/tmp/agno_agent_{self.id}.py"

            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            VENV_PY = "/opt/odoo19/venv/bin/python"

            # Important: don't pipe stdout/stderr unless you also consume them,
            # otherwise the child can block when buffers fill.
            # Use DEVNULL to avoid blocking + keep Odoo responsive.
            process = subprocess.Popen(
                [VENV_PY, script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
                close_fds=True,
            )

            time.sleep(2)

            if process.poll() is None:
                # Optionally verify the port is listening (best-effort)
                if self._ss_available():
                    # give it a bit more time for server to bind
                    for _ in range(10):
                        if self._port_is_listening(self.port):
                            break
                        time.sleep(0.3)

                self.write(
                    {
                        "is_active": True,
                        "status": "running",
                        "process_pid": process.pid,
                        "last_started": fields.Datetime.now(),
                        "error_message": False,
                        # "script_path": script_path,
                    }
                )
            else:
                # Process exited quickly; try to capture a useful error message by running synchronously
                # (we used DEVNULL above, so we re-run to capture)
                r = subprocess.run([VENV_PY, script_path], capture_output=True, text=True, check=False)
                error_msg = (r.stderr or r.stdout or "").strip()
                if not error_msg:
                    error_msg = "Agent process exited immediately without output."
                self.write({"status": "error", "error_message": f"Failed to start agent: {error_msg}"})
                raise UserError(_(f"Failed to start agent: {error_msg}"))

        except Exception as e:
            self.write({"status": "error", "error_message": str(e)})
            raise UserError(_(f"Error starting agent: {str(e)}"))

    def action_stop_agent(self):
        """Stop the Agno agent (kill process group and/or the process that owns the port)"""
        self.ensure_one()

        if not self.is_active:
            raise UserError(_("Agent is not active"))

        try:
            self.status = "stopping"

            attempted_any = False

            # 1) Try killing the process group we started
            if self.process_pid:
                attempted_any = self._kill_process_group(self.process_pid, term_wait=2.0) or attempted_any

            # 2) Ensure the port is freed (your requirement: kill process at specified port)
            if self._ss_available():
                if self._port_is_listening(self.port):
                    attempted_any = self._kill_by_port(self.port, term_wait=2.0) or attempted_any

                    # Verify again
                    if self._port_is_listening(self.port):
                        raise UserError(_(f"Could not stop agent: port {self.port} is still in use."))

            # If neither PID nor port checks worked, still mark stopped, but keep a warning
            warn = False if attempted_any else _("Stop requested, but no running process was found.")

            self.write(
                {
                    "is_active": False,
                    "status": "stopped",
                    "process_pid": 0,
                    "last_stopped": fields.Datetime.now(),
                    "error_message": warn,
                }
            )

        except Exception as e:
            self.write({"status": "error", "error_message": str(e)})
            raise UserError(_(f"Error stopping agent: {str(e)}"))

    # ------------------------
    # Script generator
    # ------------------------
    def _generate_agent_script(self):
        """Generate the Python script to run the Agno agent"""
        # NOTE: api_key must be the VALUE of env var, not its NAME.
        # We also set PYTHONUNBUFFERED for easier debugging if you later log to a file.
        script = f'''
import os
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb

os.environ.setdefault("AGNO_TELEMETRY", "false")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

api_key = os.getenv("{self.api_key_env}")  # VALUE, not the env var name

model = OpenAILike(
    id="{self.model_id}",
    base_url="{self.base_url}",
    api_key=api_key,
)

db = SqliteDb(db_file="{self.db_file}")

agent = Agent(
    name="{self.agent_name}",
    role="""{self.agent_role}""",
    model=model,
    instructions="""{self.instructions or ''}""",
    db=db,
    add_history_to_context={self.add_history_to_context},
    add_datetime_to_context={self.add_datetime_to_context},
    markdown={self.markdown},
    debug_mode={self.debug_mode},
    num_history_runs={self.num_history_runs},
)

agent_os = AgentOS(agents=[agent])
app = agent_os.get_app()

if __name__ == "__main__":
    print("Starting Agent '{self.agent_name}' on http://{self.host}:{self.port}")
    agent_os.serve(app=app, host="{self.host}", port={self.port}, reload=False)
'''
        return script

    # ------------------------
    # Cron/maintenance
    # ------------------------
    @api.model
    def check_agent_status(self):
        """Check and update status of all active agents (by port if available, otherwise by PID)"""
        active_agents = self.search([("is_active", "=", True)])

        for agent in active_agents:
            # Prefer checking by port because PID may not be the listener PID
            if agent._ss_available():
                try:
                    if not agent._get_listening_pids(agent.port):
                        agent.write(
                            {
                                "is_active": False,
                                "status": "stopped",
                                "process_pid": 0,
                                "last_stopped": fields.Datetime.now(),
                            }
                        )
                    continue
                except Exception:
                    # fall back to PID check below
                    pass

            if agent.process_pid:
                try:
                    os.kill(agent.process_pid, 0)
                except OSError:
                    agent.write(
                        {
                            "is_active": False,
                            "status": "stopped",
                            "process_pid": 0,
                            "last_stopped": fields.Datetime.now(),
                        }
                    )
            else:
                # No PID and can't check port => assume stopped
                agent.write(
                    {
                        "is_active": False,
                        "status": "stopped",
                        "process_pid": 0,
                        "last_stopped": fields.Datetime.now(),
                    }
                )

    def unlink(self):
        for record in self:
            if record.is_active:
                record.action_stop_agent()
        return super().unlink()

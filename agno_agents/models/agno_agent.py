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
        default="gpt-oss:20b",
        help="AI model identifier (e.g., qwen3:latest)",
    )
    base_url = fields.Char(
        "Base URL",
        required=True,
        default="https://chat.aiahura.com/api/v1",
        help="API base URL for the model",
    )

    api_key = fields.Char(
        "API Key",
        required=True,
        help="API key used for the model provider (stored in Odoo).",
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

    def _script_path(self) -> str:
        self.ensure_one()
        return f"/tmp/agno_agent_{self.id}.py"

    def _log_path(self) -> str:
        self.ensure_one()
        return f"/tmp/agno_agent_{self.id}.log"

    def _ss_available(self):
        try:
            subprocess.run(["ss", "-h"], capture_output=True, text=True, check=False)
            return True
        except FileNotFoundError:
            return False

    def _get_listening_pids(self, port: int):
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

    def _port_is_listening(self, port: int):
        try:
            return bool(self._get_listening_pids(port))
        except Exception:
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
        pids = self._get_listening_pids(port)
        if not pids:
            return False

        self._kill_pids(pids, signal.SIGTERM)
        time.sleep(term_wait)

        pids_after = self._get_listening_pids(port)
        if pids_after:
            self._kill_pids(pids_after, signal.SIGKILL)

        return True

    def _kill_process_group(self, pid: int, term_wait: float = 2.0):
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

        try:
            os.killpg(pgid, 0)
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError as e:
            raise UserError(_(f"No permission to SIGKILL agent process group: {e}"))

        return True

    def action_start_agent(self):
        self.ensure_one()

        if self.is_active:
            raise UserError(_("Agent is already active"))

        if self._ss_available() and self._port_is_listening(self.port):
            raise UserError(_(f"Port {self.port} is already in use. Stop the process using it or change the port."))

        try:
            self.status = "starting"
            self.error_message = False

            script_content = self._generate_agent_script()
            script_path = self._script_path()
            log_path = self._log_path()

            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            try:
                with open(log_path, "w", encoding="utf-8") as lf:
                    lf.write("")
            except Exception:
                pass

            VENV_PY = "/opt/odoo19/venv/bin/python"

            logf = open(log_path, "a", encoding="utf-8")

            process = subprocess.Popen(
                [VENV_PY, "-u", script_path],
                stdout=logf,
                stderr=logf,
                preexec_fn=os.setsid,
                close_fds=True,
            )

            time.sleep(2)
            if process.poll() is None:
                if self._ss_available():
                    for i in range(10):
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
                    }
                )
            else:
                r = subprocess.run([VENV_PY, "-u", script_path], capture_output=True, text=True, check=False)
                error_msg = (r.stderr or r.stdout or "").strip()
                if not error_msg:
                    error_msg = "Agent process exited immediately without output."
                self.write({"status": "error", "error_message": f"Failed to start agent: {error_msg}"})
                raise UserError(_(f"Failed to start agent: {error_msg}"))

        except Exception as e:
            self.write({"status": "error", "error_message": str(e)})
            raise UserError(_(f"Error starting agent: {str(e)}"))

    def action_stop_agent(self):
        self.ensure_one()

        if not self.is_active:
            raise UserError(_("Agent is not active"))

        try:
            self.status = "stopping"

            attempted_any = False

            if self.process_pid:
                attempted_any = self._kill_process_group(self.process_pid, term_wait=2.0) or attempted_any

            if self._ss_available() and self._port_is_listening(self.port):
                attempted_any = self._kill_by_port(self.port, term_wait=2.0) or attempted_any

                if self._port_is_listening(self.port):
                    raise UserError(_(f"Could not stop agent: port {self.port} is still in use."))

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

    def _generate_agent_script(self):
        """
        Generates a python script that logs:
        - configuration values
        - masked API key preview
        - httpx/httpcore debug logs (helpful for streaming failures)
        - tracebacks on crash
        """
        self.ensure_one()
        log_path = self._log_path()
        script_path = self._script_path()

        script = f'''
import os
import sys
import time
import logging
import traceback

from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb

LOG_PATH = {repr(log_path)}
SCRIPT_PATH = {repr(script_path)}

def mask_secret(value: str, show: int = 6) -> str:
    if not value:
        return "<EMPTY>"
    if len(value) <= show:
        return "*" * len(value)
    return value[:show] + ("*" * (len(value) - show))

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Enable verbose HTTP tracing (very useful for "Unknown model error" / streaming issues)
    logging.getLogger("httpx").setLevel(logging.DEBUG)
    logging.getLogger("httpcore").setLevel(logging.DEBUG)

setup_logging()
log = logging.getLogger("agno_agent")

def main():
    os.environ.setdefault("AGNO_TELEMETRY", "false")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    api_key = {repr(self.api_key or "")}

    log.info("=== Agno Agent starting ===")
    log.info("time=%s", time.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("python=%s", sys.executable)
    log.info("cwd=%s", os.getcwd())
    log.info("script_path=%s", SCRIPT_PATH)
    log.info("log_path=%s", LOG_PATH)

    log.info("AGNO_TELEMETRY=%s", os.environ.get("AGNO_TELEMETRY"))
    log.info("PYTHONUNBUFFERED=%s", os.environ.get("PYTHONUNBUFFERED"))

    log.info("agent_name=%s", {repr(self.agent_name or "")})
    log.info("host=%s", {repr(self.host or "0.0.0.0")})
    log.info("port=%s", {int(self.port)})
    log.info("model_id=%s", {repr(self.model_id or "")})
    log.info("base_url=%s", {repr(self.base_url or "")})
    log.info("db_file=%s", {repr(self.db_file or "agent.db")})

    log.info("add_history_to_context=%s", {bool(self.add_history_to_context)})
    log.info("add_datetime_to_context=%s", {bool(self.add_datetime_to_context)})
    log.info("markdown=%s", {bool(self.markdown)})
    log.info("debug_mode=%s", {bool(self.debug_mode)})
    log.info("num_history_runs=%s", {int(self.num_history_runs or 5)})

    log.info("api_key_length=%s", len(api_key))
    log.info("api_key_preview=%s", mask_secret(api_key, 6))

    model = OpenAILike(
        id={repr(self.model_id or "")},
        base_url={repr(self.base_url or "")},
        api_key=api_key,
    )

    db = SqliteDb(db_file={repr(self.db_file or "agent.db")})

    agent = Agent(
        name={repr(self.agent_name or "")},
        role={repr(self.agent_role or "")},
        model=model,
        instructions={repr(self.instructions or "")},
        db=db,
        add_history_to_context={bool(self.add_history_to_context)},
        add_datetime_to_context={bool(self.add_datetime_to_context)},
        markdown={bool(self.markdown)},
        debug_mode={bool(self.debug_mode)},
        num_history_runs={int(self.num_history_runs or 5)},
    )

    agent_os = AgentOS(agents=[agent])
    app = agent_os.get_app()

    log.info("Serving on http://%s:%s", {repr(self.host or "0.0.0.0")}, {int(self.port)})
    agent_os.serve(app=app, host={repr(self.host or "0.0.0.0")}, port={int(self.port)}, reload=False)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error("Agent crashed: %s", e)
        log.error(traceback.format_exc())
        raise
'''
        return script

    @api.model
    def check_agent_status(self):
        active_agents = self.search([("is_active", "=", True)])
        for agent in active_agents:
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

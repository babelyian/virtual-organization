import os
import re
import json
import signal
import subprocess
import time
import logging

from odoo import _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class AgnoAgentService:


    DEFAULT_VENV_PY = "/usr/bin/python3"

    @staticmethod
    def script_path(agent_id: int):

        return f"/tmp/agno_agent_{agent_id}.py"

    @staticmethod
    def log_path(agent_id: int):
        return f"/tmp/agno_agent_{agent_id}.log"

    @staticmethod
    def config_path(agent_id: int):
        return f"/tmp/agno_agent_{agent_id}.json"

    @staticmethod
    def runner_path():

        return os.path.join(os.path.dirname(__file__), "agno_runner.py")

    @staticmethod
    def ss_available():
        try:
            subprocess.run(["ss", "-h"], capture_output=True, text=True, check=False)
            return True
        except FileNotFoundError:
            return False

    @classmethod
    def get_listening_pids(cls, port: int):
        if not cls.ss_available():
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

    @classmethod
    def port_is_listening(cls, port: int):
        try:
            return bool(cls.get_listening_pids(port))
        except Exception:
            return True

    @staticmethod
    def _kill_pids(pids, sig):
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
            except PermissionError as e:
                raise UserError(_(f"No permission to kill pid {pid}: {e}"))

    @classmethod
    def kill_by_port(cls, port: int, term_wait: float = 2.0):
        pids = cls.get_listening_pids(port)
        if not pids:
            return False

        cls._kill_pids(pids, signal.SIGTERM)
        time.sleep(term_wait)

        pids_after = cls.get_listening_pids(port)
        if pids_after:
            cls._kill_pids(pids_after, signal.SIGKILL)

        return True

    @staticmethod
    def kill_process_group(pid: int, term_wait: float = 2.0):
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

    @classmethod
    def write_config(cls, agent) -> str:

        cfg_path = cls.config_path(agent.id)
        log_path = cls.log_path(agent.id)

        cfg = {
            "log_path": log_path,
            "agent_name": agent.agent_name or "",
            "agent_role": agent.agent_role or "",
            "instructions": agent.instructions or "",
            "model_name": agent.model_name or "",
            "base_url": agent.base_url or "",
            "api_key": agent.api_key or "",
            "db_file": agent.db_file or "agent.db",
            "host": agent.host or "0.0.0.0",
            "port": int(agent.port),
            "add_history_to_context": bool(agent.add_history_to_context),
            "add_datetime_to_context": bool(agent.add_datetime_to_context),
            "markdown": bool(agent.markdown),
            "debug_mode": bool(agent.debug_mode),
            "num_history_runs": int(agent.num_history_runs or 5),
        }

        try:
            with open(log_path, "w", encoding="utf-8") as lf:
                lf.write("")
        except Exception:
            pass

        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

        try:
            os.chmod(cfg_path, 0o600)
        except Exception:
            pass

        return cfg_path

    @classmethod
    def start_agent_process(cls, agent, venv_py: str = None):
  
        venv_py = venv_py or cls.DEFAULT_VENV_PY

        runner = cls.runner_path()
        if not os.path.exists(runner):
            raise UserError(_(f"Runner file not found: {runner}"))

        if cls.ss_available() and cls.port_is_listening(agent.port):
            raise UserError(
                _(f"Port {agent.port} is already in use. Stop the process using it or change the port.")
            )

        cfg_path = cls.write_config(agent)
        log_path = cls.log_path(agent.id)

        logf = open(log_path, "a", encoding="utf-8")

        process = subprocess.Popen(
            [venv_py, "-u", runner, "--config", cfg_path],
            stdout=logf,
            stderr=logf,
            preexec_fn=os.setsid,
            close_fds=True,
        )

        time.sleep(2)
        if process.poll() is not None:
            r = subprocess.run(
                [venv_py, "-u", runner, "--config", cfg_path],
                capture_output=True,
                text=True,
                check=False,
            )
            error_msg = (r.stderr or r.stdout or "").strip() or "Agent process exited immediately without output."
            raise UserError(_(f"Failed to start agent: {error_msg}"))

        if cls.ss_available():
            for _ in range(10):
                if cls.port_is_listening(agent.port):
                    break
                time.sleep(0.3)

        return process.pid

    @classmethod
    def stop_agent_process(cls, agent, term_wait: float = 2.0):

        attempted_any = False

        if agent.process_pid:
            attempted_any = cls.kill_process_group(agent.process_pid, term_wait=term_wait) or attempted_any

        if cls.ss_available() and cls.port_is_listening(agent.port):
            attempted_any = cls.kill_by_port(agent.port, term_wait=term_wait) or attempted_any

            if cls.port_is_listening(agent.port):
                raise UserError(_(f"Could not stop agent: port {agent.port} is still in use."))

        return attempted_any

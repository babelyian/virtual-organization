# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import os
import json
import logging
import requests

from odoo import models, fields, _
from odoo.exceptions import UserError

from ..services.agno_services import AgnoAgentService

_logger = logging.getLogger(__name__)


class AgnoAction(models.AbstractModel):

    _name = "agno.action"
    _description = "Agno Agent Actions"

    @staticmethod
    def _pid_exists(pid: int) -> bool:
        if not pid or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False

    def is_agent_alive(self, agent) -> bool:

        agent.ensure_one()

        if AgnoAgentService.ss_available():
            try:
                return bool(AgnoAgentService.get_listening_pids(agent.port))
            except Exception as e:
                _logger.debug("Port liveness check failed for agent %s: %s", agent.id, e)
                return self._pid_exists(agent.process_pid)

        return self._pid_exists(agent.process_pid)

    def start_agents(self, agents):

        if not agents:
            return True

        for agent in agents:
            agent.ensure_one()

            if agent.is_active:
                raise UserError(_("Agent '%s' is already active.") % (agent.agent_name or agent.id))

            if not agent.api_key:
                raise UserError(_("API Key is required to start agent '%s'.") % (agent.agent_name or agent.id))

            agent.write({"status": "starting", "error_message": False})

            try:
                pid = AgnoAgentService.start_agent_process(agent)
                agent.write(
                    {
                        "is_active": True,
                        "status": "running",
                        "process_pid": pid,
                        "last_started": fields.Datetime.now(),
                        "error_message": False,
                    }
                )
            except Exception as e:
                agent.write({"status": "error", "error_message": str(e)})
                if isinstance(e, UserError):
                    raise
                raise UserError(_("Error starting agent '%s': %s") % (agent.agent_name or agent.id, e))

        return True

    def stop_agents(self, agents):

        if not agents:
            return True

        for agent in agents:
            agent.ensure_one()

            if not agent.is_active:
                raise UserError(_("Agent '%s' is not active.") % (agent.agent_name or agent.id))

            agent.write({"status": "stopping"})

            try:
                attempted = AgnoAgentService.stop_agent_process(agent, term_wait=2.0)
                warn = False if attempted else _("Stop requested, but no running process was found.")

                agent.write(
                    {
                        "is_active": False,
                        "status": "stopped",
                        "process_pid": 0,
                        "last_stopped": fields.Datetime.now(),
                        "error_message": warn,
                    }
                )
            except Exception as e:
                agent.write({"status": "error", "error_message": str(e)})
                if isinstance(e, UserError):
                    raise
                raise UserError(_("Error stopping agent '%s': %s") % (agent.agent_name or agent.id, e))

        return True

    def refresh_agents(self, agents):

        if not agents:
            return True

        now = fields.Datetime.now()

        for agent in agents:
            agent.ensure_one()
            try:
                alive = self.is_agent_alive(agent)
            except Exception as e:
                _logger.debug("refresh_agents liveness check failed for agent %s: %s", agent.id, e)
                continue

            if not alive and agent.is_active:
                agent.write(
                    {
                        "is_active": False,
                        "status": "stopped",
                        "process_pid": 0,
                        "last_stopped": now,
                    }
                )
        return True


    def run_prompt(self, agent, user_message: str, session_id: str = None, timeout: int = 120) -> str:

        if not agent:
            raise UserError(_("No agent provided."))

        agent.ensure_one()

        host = agent.host or "127.0.0.1"
        if host == "0.0.0.0":
            host = "127.0.0.1"

        if not agent.agent_name:
            raise UserError(_("Agent has no agent_name."))

        url = f"http://{host}:{agent.port}/agents/{agent.agent_name}/runs"
        session_id = session_id or "odoo_cron_broadcast"

        payload = {
            "message": (user_message or "").strip(),
            "session_id": session_id,
            "stream": True,
        }

        _logger.info(
            "run_prompt → Agno [%s:%s/%s] session=%s msg=%s",
            host, agent.port, agent.agent_name, session_id, (user_message or "")[:120],
        )

        try:
            response = requests.post(
                url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=timeout,
                stream=True,
            )
            response.raise_for_status()

            full_content = ""
            for line in response.iter_lines():
                if not line:
                    continue

                decoded_line = line.decode("utf-8", errors="ignore").strip()
                _logger.debug("SSE line: %s", decoded_line)

                if not decoded_line.startswith("data:"):
                    continue

                data_str = decoded_line[5:].strip()

                try:
                    event_data = json.loads(data_str)
                    ev = event_data.get("event")

                    if ev == "RunContent":
                        full_content += event_data.get("content", "") or ""
                    elif ev == "RunCompleted":
                        final = (event_data.get("content") or "").strip()
                        full_content = final or full_content.strip()
                        break

                except json.JSONDecodeError:
                    full_content += data_str + "\n"

            return (full_content or "").strip()

        except requests.exceptions.RequestException as e:
            _logger.error("Agno agent communication failed: %s", str(e))
            msg = str(e)
            if "Connection refused" in msg:
                msg = "Cannot connect to agent server. Is it running?"
            raise UserError(_(msg))


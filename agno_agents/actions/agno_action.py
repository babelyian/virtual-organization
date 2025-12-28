# -*- coding: utf-8 -*-
import os
import logging

from odoo import models, fields, _
from odoo.exceptions import UserError

from ..services.agno_services import AgnoAgentService

_logger = logging.getLogger(__name__)


class AgnoAction(models.AbstractModel):
    """
    UI/Business actions invoked by ir.actions.server.

    - start_agents(records)
    - stop_agents(records)
    - is_agent_alive(agent) helper (used by agno.agent.check_agent_status)
    """
    _name = "agno.action"
    _description = "Agno Agent Actions"

    # ---------------------------
    # Helpers
    # ---------------------------
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
            # PID exists but we can't signal it; treat as alive to avoid false negatives.
            return True
        except OSError:
            return False

    def is_agent_alive(self, agent) -> bool:
        """
        Returns True if agent seems alive:
        - prefer port check via ss if available
        - fallback to PID existence
        """
        agent.ensure_one()

        if AgnoAgentService.ss_available():
            try:
                return bool(AgnoAgentService.get_listening_pids(agent.port))
            except Exception as e:
                _logger.debug("Port liveness check failed for agent %s: %s", agent.id, e)
                return self._pid_exists(agent.process_pid)

        return self._pid_exists(agent.process_pid)

    # ---------------------------
    # Actions called by Server Actions
    # ---------------------------
    def start_agents(self, agents):
        """
        Start selected agno.agent record(s).
        Updates DB state (status/is_active/process_pid/last_started/error_message).
        """
        if not agents:
            return True

        for agent in agents:
            agent.ensure_one()

            if agent.is_active:
                raise UserError(_("Agent '%s' is already active.") % (agent.agent_name or agent.id))

            if not agent.api_key:
                raise UserError(_("API Key is required to start agent '%s'.") % (agent.agent_name or agent.id))

            # DB update: starting
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
        """
        Stop selected agno.agent record(s).
        Updates DB state (status/is_active/process_pid/last_stopped/error_message).
        """
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
        """
        Optional helper for a 'Refresh Status' UI button.
        (Simply calls liveness check and sets stopped if dead.)
        """
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

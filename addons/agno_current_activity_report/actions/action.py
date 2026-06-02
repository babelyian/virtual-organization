# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, _
from odoo.exceptions import UserError

from ..services.external_client import ExternalAgentClient

_logger = logging.getLogger(__name__)


class AgnoAction(models.AbstractModel):
    _name = "agno.action"
    _description = "Agno Agent Actions"

    def is_agent_alive(self, agent):
        """Check if agent is running via external service"""
        agent.ensure_one()
        try:
            status = ExternalAgentClient.get_agent_status(agent)
            return status == 'running'
        except Exception as e:
            _logger.debug("Status check failed for agent %s: %s", agent.id, e)
            return False

    def start_agents(self, agents):
        """Start agents using external service"""
        if not agents:
            return True

        for agent in agents:
            agent.ensure_one()

            if agent.is_active:
                raise UserError(_("Agent '%s' is already active.") % (agent.agent_name or agent.id))

            if not agent.api_key:
                raise UserError(_("API Key is required to start agent '%s'.") % (agent.agent_name or agent.id))

            if not agent.external_service_url:
                raise UserError(_("External service URL is required for agent '%s'.") % (agent.agent_name or agent.id))

            agent.write({"status": "starting", "error_message": False})

            try:
                result = ExternalAgentClient.start_agent(agent)

                if result.get('success', False):
                    agent.write({
                        "is_active": True,
                        "status": "running",
                        "last_started": fields.Datetime.now(),
                        "error_message": False,
                    })
                else:
                    raise UserError(result.get('error', 'Unknown error'))

            except Exception as e:
                agent.write({"status": "error", "error_message": str(e)})
                if isinstance(e, UserError):
                    raise
                raise UserError(_("Error starting agent '%s': %s") % (agent.agent_name or agent.id, e))

        return True

    def stop_agents(self, agents):
        """Stop agents using external service"""
        if not agents:
            return True

        for agent in agents:
            agent.ensure_one()

            if not agent.is_active:
                raise UserError(_("Agent '%s' is not active.") % (agent.agent_name or agent.id))

            agent.write({"status": "stopping"})

            try:
                result = ExternalAgentClient.stop_agent(agent)

                agent.write({
                    "is_active": False,
                    "status": "stopped",
                    "last_stopped": fields.Datetime.now(),
                    "error_message": False if result.get('success', False) else result.get('error', ''),
                })

            except Exception as e:
                agent.write({"status": "error", "error_message": str(e)})
                if isinstance(e, UserError):
                    raise
                raise UserError(_("Error stopping agent '%s': %s") % (agent.agent_name or agent.id, e))

        return True

    def refresh_agents(self, agents):
        """Refresh agent statuses from external service"""
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
                agent.write({
                    "is_active": False,
                    "status": "stopped",
                    "last_stopped": now,
                })
        return True

    def run_prompt(self, agent, user_message: str, session_id: str = None, timeout: int = 120) -> str:
        """Run prompt using external service"""
        if not agent:
            raise UserError(_("No agent provided."))

        agent.ensure_one()

        if not agent.external_service_url:
            raise UserError(_("External service URL not configured for agent '%s'") % agent.agent_name)

        try:
            response = ExternalAgentClient.run_prompt(agent, user_message, session_id)
            return response
        except Exception as e:
            _logger.error("External agent communication failed: %s", str(e))
            raise UserError(_("Failed to communicate with agent: %s") % str(e))
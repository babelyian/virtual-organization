import logging
import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ExternalAgentClient:
    """Client for external agent service (Django/FastAPI)"""

    @staticmethod
    def _get_agent_endpoint(agent, endpoint):
        """Build full endpoint URL for an agent"""
        base_url = agent.external_service_url.rstrip('/')
        # Use external_agent_id if provided, otherwise use str(agent.id)
        agent_id = agent.external_agent_id or str(agent.id)
        return f"{base_url}/agents/{agent_id}/{endpoint.lstrip('/')}"

    @staticmethod
    def _make_request(url, method='GET', data=None, timeout=30):
        """Make HTTP request to external service"""
        try:
            headers = {'Content-Type': 'application/json'}

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            raise UserError(_("Cannot connect to external agent service at %s") % url)
        except requests.exceptions.Timeout:
            raise UserError(_("Timeout connecting to external agent service"))
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise UserError(_("Agent not found in external service"))
            raise UserError(_("HTTP error: %s") % str(e))
        except Exception as e:
            raise UserError(_("Error: %s") % str(e))

    @classmethod
    def start_agent(cls, agent):
        """Start agent on external service"""
        url = cls._get_agent_endpoint(agent, 'start')
        _logger.info(f"Calling external service: {url}")
        # Prepare configuration for external service
        config = {
            'agent_name': agent.agent_name,
            'instructions': str(agent.instructions or ""),
            'model_name': agent.model_name,
            'base_url': agent.base_url,
            'api_key': agent.api_key,
            'add_history_to_context': agent.add_history_to_context,
            'add_datetime_to_context': agent.add_datetime_to_context,
            'markdown': agent.markdown,
            'debug_mode': agent.debug_mode,
            'num_history_runs': agent.num_history_runs,
        }
        _logger.info(f"Config: {config}")

        result = cls._make_request(url, method='POST', data=config)
        return result

    @classmethod
    def stop_agent(cls, agent):
        """Stop agent on external service"""
        url = cls._get_agent_endpoint(agent, 'stop')
        result = cls._make_request(url, method='POST')
        return result

    @classmethod
    def get_agent_status(cls, agent):
        """Get agent status from external service"""
        url = cls._get_agent_endpoint(agent, 'status')
        result = cls._make_request(url, method='GET')
        return result.get('status', 'unknown')

    @classmethod
    def run_prompt(cls, agent, message, session_id=None):
        """Send prompt to agent"""
        url = cls._get_agent_endpoint(agent, 'run')
        data = {
            'message': message,
            'session_id': session_id or f"odoo_{agent.id}",
        }
        result = cls._make_request(url, method='POST', data=data, timeout=120)
        return result.get('response', '')
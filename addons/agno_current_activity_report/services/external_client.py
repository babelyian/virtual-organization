import requests
import logging
from odoo import _

_logger = logging.getLogger(__name__)


class ExternalAgentClient:
    """Client for communicating with external agent service"""

    @staticmethod
    def _make_request(service_url, endpoint, method='POST', data=None, timeout=30):
        """Make HTTP request to external service"""
        url = f"{service_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            'Content-Type': 'application/json',
        }

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            raise Exception(_("Cannot connect to external agent service at %s") % service_url)
        except requests.exceptions.Timeout:
            raise Exception(_("Timeout connecting to external agent service"))
        except requests.exceptions.HTTPError as e:
            raise Exception(_("HTTP error: %s") % str(e))
        except Exception as e:
            raise Exception(_("Error: %s") % str(e))

    @staticmethod
    def get_agent_status(agent):
        """Get agent status from external service"""
        result = ExternalAgentClient._make_request(
            agent.external_service_url,
            f"/agents/{agent.external_agent_id}/status",
            method='GET',
        )
        return result.get('status', 'unknown')

    @staticmethod
    def start_agent(agent):
        """Start agent on external service"""
        result = ExternalAgentClient._make_request(
            agent.external_service_url,
            f"/agents/{agent.external_agent_id}/start",
            data={
                'config': {
                    'model_name': agent.model_name,
                    'base_url': agent.base_url,
                    'instructions': agent.instructions,
                    # Add other configuration as needed
                }
            },
        )
        return result

    @staticmethod
    def stop_agent(agent):
        """Stop agent on external service"""
        result = ExternalAgentClient._make_request(
            agent.external_service_url,
            f"/agents/{agent.external_agent_id}/stop",
        )
        return result

    @staticmethod
    def run_prompt(agent, message, session_id=None):
        """Send prompt to agent"""
        data = {
            'message': message,
            'session_id': session_id,
        }
        result = ExternalAgentClient._make_request(
            agent.external_service_url,
            f"/agents/{agent.external_agent_id}/run",
            data=data,
        )
        return result.get('response', '')
import hmac
import json
from odoo import http, fields, api, SUPERUSER_ID
from odoo.http import request
from odoo.exceptions import UserError

from ..services.external_client import ExternalAgentClient

AGNO_HTTP_TOKEN = "CHANGE_ME_TO_A_LONG_RANDOM_STRING"


def _check_token():
    token = request.httprequest.headers.get("X-Agno-Token", "")
    if not hmac.compare_digest(token, AGNO_HTTP_TOKEN):
        raise UserError("Invalid or missing X-Agno-Token header")


def _su_env():
    ctx = dict(request.env.context or {})
    return api.Environment(request.env.cr, SUPERUSER_ID, ctx)


def _get_payload(kwargs=None):
    payload = {}
    if kwargs:
        payload.update(kwargs)

    try:
        raw = request.httprequest.get_data(as_text=True) or ""
        raw = raw.strip()
        if raw:
            data = json.loads(raw)
            if isinstance(data, dict):
                if isinstance(data.get("params"), dict):
                    payload.update(data["params"])
                else:
                    payload.update(data)
    except Exception:
        pass

    return payload


class AgnoAgentController(http.Controller):

    @http.route("/agno_agents/status", type="json", auth="none", methods=["POST"], csrf=False)
    def get_agents_status(self, **kwargs):
        try:
            _check_token()
            env = _su_env()

            agents = env["agno.current.activity.report"].search([])

            result = []
            for agent in agents:
                # Get status from external service
                try:
                    ext_status = ExternalAgentClient.get_agent_status(agent)
                except Exception:
                    ext_status = agent.status

                result.append({
                    "id": agent.id,
                    "name": agent.agent_name,
                    "status": ext_status,
                    "is_active": agent.is_active,
                    "external_service_url": agent.external_service_url,
                    "model_name": agent.model_name,
                    "last_started": agent.last_started.isoformat() if agent.last_started else None,
                    "error_message": agent.error_message or None,
                })

            return {"success": True, "agents": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @http.route("/agno_agents/create", type="json", auth="none", methods=["POST"], csrf=False)
    def create_agent(self, **kwargs):
        try:
            _check_token()
            env = _su_env()

            payload = _get_payload(kwargs)

            agent_name = (payload.get("agent_name") or "").strip()
            api_key = (payload.get("api_key") or "").strip()
            external_service_url = (payload.get("external_service_url") or "").strip()

            if not agent_name:
                return {"success": False, "error": "agent_name is required"}
            if not api_key:
                return {"success": False, "error": "api_key is required"}
            if not external_service_url:
                return {"success": False, "error": "external_service_url is required"}

            vals = {
                "agent_name": agent_name,
                "instructions": payload.get("instructions") or "",
                "model_name": payload.get("model_name") or "gemma-3:27b",
                "base_url": payload.get("base_url") or "https://api.metisai.ir/openai/v1",
                "api_key": api_key,
                "external_service_url": external_service_url,
                "external_agent_id": payload.get("external_agent_id") or "",
                "add_history_to_context": bool(payload.get("add_history_to_context", True)),
                "add_datetime_to_context": bool(payload.get("add_datetime_to_context", False)),
                "markdown": bool(payload.get("markdown", True)),
                "debug_mode": bool(payload.get("debug_mode", False)),
                "num_history_runs": int(payload.get("num_history_runs") or 5),
                "is_active": False,
                "status": "stopped",
                "error_message": False,
            }

            agent = env["agno.current.activity.report"].create(vals)

            return {
                "success": True,
                "message": "Agent created successfully",
                "agent": {
                    "id": agent.id,
                    "name": agent.agent_name,
                    "status": agent.status,
                    "is_active": agent.is_active,
                    "external_service_url": agent.external_service_url,
                    "model_name": agent.model_name,
                    "base_url": agent.base_url,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @http.route("/agno_agents/start/<int:agent_id>", type="json", auth="none", methods=["POST"], csrf=False)
    def start_agent(self, agent_id, **kwargs):
        try:
            _check_token()
            env = _su_env()

            agent = env["agno.current.activity.report"].browse(agent_id)
            if not agent.exists():
                return {"success": False, "error": "Agent not found"}

            if agent.is_active:
                return {"success": False, "error": "Agent is already active"}

            if not agent.api_key:
                return {"success": False, "error": "API Key is required to start the agent."}

            if not agent.external_service_url:
                return {"success": False, "error": "External service URL is required."}

            agent.write({"status": "starting", "error_message": False})

            # Start agent via external service
            result = ExternalAgentClient.start_agent(agent)

            if result.get('success', False):
                agent.write({
                    "is_active": True,
                    "status": "running",
                    "last_started": fields.Datetime.now(),
                    "error_message": False,
                })

                return {
                    "success": True,
                    "message": f"Agent {agent.agent_name} started successfully",
                    "external_service_url": agent.external_service_url,
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                agent.write({"status": "error", "error_message": error_msg})
                return {"success": False, "error": error_msg}

        except Exception as e:
            try:
                env = _su_env()
                env["agno.current.activity.report"].browse(agent_id).write({"status": "error", "error_message": str(e)})
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    @http.route("/agno_agents/stop/<int:agent_id>", type="json", auth="none", methods=["POST"], csrf=False)
    def stop_agent(self, agent_id, **kwargs):
        try:
            _check_token()
            env = _su_env()

            agent = env["agno.current.activity.report"].browse(agent_id)
            if not agent.exists():
                return {"success": False, "error": "Agent not found"}

            if not agent.is_active:
                return {"success": False, "error": "Agent is not active"}

            agent.write({"status": "stopping"})

            # Stop agent via external service
            result = ExternalAgentClient.stop_agent(agent)

            agent.write({
                "is_active": False,
                "status": "stopped",
                "last_stopped": fields.Datetime.now(),
                "error_message": "" if result.get('success', False) else result.get('error', ''),
            })

            if result.get('success', False):
                return {"success": True, "message": f"Agent {agent.agent_name} stopped successfully"}
            else:
                return {"success": False, "error": result.get('error', 'Unknown error')}

        except Exception as e:
            try:
                env = _su_env()
                env["agno.current.activity.report"].browse(agent_id).write({"status": "error", "error_message": str(e)})
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    @http.route("/agno_agents/agent/<int:agent_id>/info", type="json", auth="none", methods=["POST"], csrf=False)
    def get_agent_info(self, agent_id, **kwargs):
        try:
            _check_token()
            env = _su_env()

            agent = env["agno.current.activity.report"].browse(agent_id)
            if not agent.exists():
                return {"success": False, "error": "Agent not found"}

            # Get fresh status from external service
            try:
                ext_status = ExternalAgentClient.get_agent_status(agent)
            except Exception:
                ext_status = agent.status

            return {
                "success": True,
                "agent": {
                    "id": agent.id,
                    "name": agent.agent_name,
                    "instructions": agent.instructions,
                    "model_name": agent.model_name,
                    "base_url": agent.base_url,
                    "status": ext_status,
                    "is_active": agent.is_active,
                    "external_service_url": agent.external_service_url,
                    "last_started": agent.last_started.isoformat() if agent.last_started else None,
                    "last_stopped": agent.last_stopped.isoformat() if agent.last_stopped else None,
                    "error_message": agent.error_message,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
import hmac
import json
from odoo import http, fields, api, SUPERUSER_ID
from odoo.http import request
from odoo.exceptions import UserError

from ..services.agno_services import AgnoAgentService

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

            agents = env["agno.agent"].search([])

            result = []
            for agent in agents:
                result.append({
                    "id": agent.id,
                    "name": agent.agent_name,
                    "status": agent.status,
                    "is_active": agent.is_active,
                    "port": agent.port,
                    "model_id": agent.model_id,
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
            agent_role = (payload.get("agent_role") or "").strip()
            api_key = (payload.get("api_key") or "").strip()

            if not agent_name:
                return {"success": False, "error": "agent_name is required"}
            if not agent_role:
                return {"success": False, "error": "agent_role is required"}
            if not api_key:
                return {"success": False, "error": "api_key is required"}

            vals = {
                "agent_name": agent_name,
                "agent_role": agent_role,
                "instructions": payload.get("instructions") or "",

                "model_id": payload.get("model_id") or "gpt-oss:20b",
                "base_url": payload.get("base_url") or "https://api.metisai.ir/openai/v1",
                "api_key": api_key,

                "port": int(payload.get("port") or 7777),
                "host": payload.get("host") or "0.0.0.0",

                "db_file": payload.get("db_file") or "agent.db",

                "add_history_to_context": bool(payload.get("add_history_to_context", True)),
                "add_datetime_to_context": bool(payload.get("add_datetime_to_context", False)),
                "markdown": bool(payload.get("markdown", True)),
                "debug_mode": bool(payload.get("debug_mode", False)),
                "num_history_runs": int(payload.get("num_history_runs") or 5),

                "is_active": False,
                "status": "stopped",
                "process_pid": 0,
                "error_message": False,
            }

            if AgnoAgentService.ss_available() and AgnoAgentService.port_is_listening(vals["port"]):
                return {"success": False, "error": f"Port {vals['port']} is already in use."}

            agent = env["agno.agent"].create(vals)

            return {
                "success": True,
                "message": "Agent created successfully",
                "agent": {
                    "id": agent.id,
                    "name": agent.agent_name,
                    "status": agent.status,
                    "is_active": agent.is_active,
                    "port": agent.port,
                    "host": agent.host,
                    "model_id": agent.model_id,
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

            agent = env["agno.agent"].browse(agent_id)
            if not agent.exists():
                return {"success": False, "error": "Agent not found"}

            if agent.is_active:
                return {"success": False, "error": "Agent is already active"}

            if not agent.api_key:
                return {"success": False, "error": "API Key is required to start the agent."}

            agent.write({"status": "starting", "error_message": False})

            pid = AgnoAgentService.start_agent_process(agent)

            agent.write({
                "is_active": True,
                "status": "running",
                "process_pid": pid,
                "last_started": fields.Datetime.now(),
                "error_message": False,
            })

            return {
                "success": True,
                "message": f"Agent {agent.agent_name} started successfully",
                "pid": pid,
                "host": agent.host,
                "port": agent.port,
            }

        except Exception as e:
            try:
                env = _su_env()
                env["agno.agent"].browse(agent_id).write({"status": "error", "error_message": str(e)})
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    @http.route("/agno_agents/stop/<int:agent_id>", type="json", auth="none", methods=["POST"], csrf=False)
    def stop_agent(self, agent_id, **kwargs):
        try:
            _check_token()
            env = _su_env()

            agent = env["agno.agent"].browse(agent_id)
            if not agent.exists():
                return {"success": False, "error": "Agent not found"}

            if not agent.is_active:
                return {"success": False, "error": "Agent is not active"}

            agent.write({"status": "stopping"})

            attempted = AgnoAgentService.stop_agent_process(agent, term_wait=2.0)
            warn = False if attempted else "Stop requested, but no running process was found."

            agent.write({
                "is_active": False,
                "status": "stopped",
                "process_pid": 0,
                "last_stopped": fields.Datetime.now(),
                "error_message": warn,
            })

            return {"success": True, "message": f"Agent {agent.agent_name} stopped successfully"}

        except Exception as e:
            try:
                env = _su_env()
                env["agno.agent"].browse(agent_id).write({"status": "error", "error_message": str(e)})
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    @http.route("/agno_agents/agent/<int:agent_id>/info", type="json", auth="none", methods=["POST"], csrf=False)
    def get_agent_info(self, agent_id, **kwargs):
        try:
            _check_token()
            env = _su_env()

            agent = env["agno.agent"].browse(agent_id)
            if not agent.exists():
                return {"success": False, "error": "Agent not found"}

            return {
                "success": True,
                "agent": {
                    "id": agent.id,
                    "name": agent.agent_name,
                    "role": agent.agent_role,
                    "instructions": agent.instructions,
                    "model_id": agent.model_id,
                    "base_url": agent.base_url,
                    "status": agent.status,
                    "is_active": agent.is_active,
                    "port": agent.port,
                    "host": agent.host,
                    "last_started": agent.last_started.isoformat() if agent.last_started else None,
                    "last_stopped": agent.last_stopped.isoformat() if agent.last_stopped else None,
                    "error_message": agent.error_message,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

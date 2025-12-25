import hmac
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


class AgnoAgentController(http.Controller):

    @http.route("/agno_agents/status", type="json", auth="none", methods=["POST"], csrf=False)
    def get_agents_status(self, **kwargs):
        try:
            _check_token()
            env = _su_env()

            agents = env["agno.agent"].search([])

            result = []
            for agent in agents:
                result.append(
                    {
                        "id": agent.id,
                        "name": agent.agent_name,
                        "status": agent.status,
                        "is_active": agent.is_active,
                        "port": agent.port,
                        "model_id": agent.model_id,
                        "last_started": agent.last_started.isoformat() if agent.last_started else None,
                        "error_message": agent.error_message or None,
                    }
                )

            return {"success": True, "agents": result}

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

            agent.write(
                {
                    "is_active": True,
                    "status": "running",
                    "process_pid": pid,
                    "last_started": fields.Datetime.now(),
                    "error_message": False,
                }
            )

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

            agent.write(
                {
                    "is_active": False,
                    "status": "stopped",
                    "process_pid": 0,
                    "last_stopped": fields.Datetime.now(),
                    "error_message": warn,
                }
            )

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

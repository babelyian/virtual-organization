import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AgnoAgent(models.Model):
    _name = "agno.agent"
    _description = "Agno Agent Configuration"
    _rec_name = "agent_name"
    _inherit = []

    agent_name = fields.Char("Agent Name", required=True, help="Name of the Agno agent")
    agent_role = fields.Text("Agent Role", required=True, help="Description of the agent's role and capabilities")
    instructions = fields.Text("Instructions", help="Additional instructions for the agent")

    model_id = fields.Char("Model ID", required=True, default="gpt-oss:20b", help="AI model identifier")
    base_url = fields.Char("Base URL", required=True, default="https://chat.aiahura.com/api/v1", help="API base URL")
    api_key = fields.Char("API Key", required=True, help="API key used for the model provider (stored in Odoo).")

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
        for rec in self:
            if not rec.agent_name or not rec.agent_name.strip():
                raise ValidationError(_("Agent name cannot be empty"))

    @api.constrains("port")
    def _check_port(self):
        for rec in self:
            if rec.port < 1 or rec.port > 65535:
                raise ValidationError(_("Port must be between 1 and 65535"))

    @api.model
    def check_agent_status(self):

        action = self.env["agno.action"]
        active_agents = self.search([("is_active", "=", True)])
        now = fields.Datetime.now()

        for agent in active_agents:
            try:
                alive = action.is_agent_alive(agent)
            except Exception as e:
                _logger.debug("check_agent_status liveness check failed for agent %s: %s", agent.id, e)
                continue

            if not alive:
                agent.write(
                    {
                        "is_active": False,
                        "status": "stopped",
                        "process_pid": 0,
                        "last_stopped": now,
                    }
                )

    def unlink(self):

        active = self.filtered("is_active")
        if active:
            try:
                self.env["agno.action"].stop_agents(active)
            except Exception as e:
                _logger.warning("Failed to stop some agents before unlink: %s", e)
        return super().unlink()

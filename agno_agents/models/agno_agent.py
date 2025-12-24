import os
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from ..services.agno_services import AgnoAgentService

_logger = logging.getLogger(__name__)


class AgnoAgent(models.Model):
    _name = "agno.agent"
    _description = "Agno Agent Configuration"
    _rec_name = "agent_name"
    _inherit = []

    agent_name = fields.Char("Agent Name", required=True, help="Name of the Agno agent")
    agent_role = fields.Text(
        "Agent Role",
        required=True,
        help="Description of the agent's role and capabilities",
    )
    instructions = fields.Text("Instructions", help="Additional instructions for the agent")

    model_id = fields.Char(
        "Model ID",
        required=True,
        default="gpt-oss:20b",
        help="AI model identifier (e.g., qwen3:latest)",
    )
    base_url = fields.Char(
        "Base URL",
        required=True,
        default="https://chat.aiahura.com/api/v1",
        help="API base URL for the model",
    )

    api_key = fields.Char(
        "API Key",
        required=True,
        help="API key used for the model provider (stored in Odoo).",
    )

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
        for record in self:
            if not record.agent_name or not record.agent_name.strip():
                raise ValidationError(_("Agent name cannot be empty"))

    @api.constrains("port")
    def _check_port(self):
        for record in self:
            if record.port < 1 or record.port > 65535:
                raise ValidationError(_("Port must be between 1 and 65535"))

    def action_start_agent(self):

        for rec in self:
            rec._action_start_one()

    def _action_start_one(self):
        self.ensure_one()

        if self.is_active:
            raise UserError(_("Agent is already active"))

        if not self.api_key:
            raise UserError(_("API Key is required to start the agent."))

        self.write({"status": "starting", "error_message": False})

        try:
            pid = AgnoAgentService.start_agent_process(self)
            self.write(
                {
                    "is_active": True,
                    "status": "running",
                    "process_pid": pid,
                    "last_started": fields.Datetime.now(),
                    "error_message": False,
                }
            )
        except Exception as e:
            self.write({"status": "error", "error_message": str(e)})
            if isinstance(e, UserError):
                raise
            raise UserError(_(f"Error starting agent: {e}"))

    def action_stop_agent(self):

        for rec in self:
            rec._action_stop_one()

    def _action_stop_one(self):
        self.ensure_one()

        if not self.is_active:
            raise UserError(_("Agent is not active"))

        self.write({"status": "stopping"})

        try:
            attempted = AgnoAgentService.stop_agent_process(self, term_wait=2.0)
            warn = False if attempted else _("Stop requested, but no running process was found.")

            self.write(
                {
                    "is_active": False,
                    "status": "stopped",
                    "process_pid": 0,
                    "last_stopped": fields.Datetime.now(),
                    "error_message": warn,
                }
            )
        except Exception as e:
            self.write({"status": "error", "error_message": str(e)})
            if isinstance(e, UserError):
                raise
            raise UserError(_(f"Error stopping agent: {e}"))


    @api.model
    def check_agent_status(self):

        active_agents = self.search([("is_active", "=", True)])
        ss_ok = AgnoAgentService.ss_available()

        for agent in active_agents:
            if ss_ok:
                try:
                    if not AgnoAgentService.get_listening_pids(agent.port):
                        agent.write(
                            {
                                "is_active": False,
                                "status": "stopped",
                                "process_pid": 0,
                                "last_stopped": fields.Datetime.now(),
                            }
                        )
                    continue
                except Exception:
                    pass

            if agent.process_pid:
                try:
                    os.kill(agent.process_pid, 0)
                except OSError:
                    agent.write(
                        {
                            "is_active": False,
                            "status": "stopped",
                            "process_pid": 0,
                            "last_stopped": fields.Datetime.now(),
                        }
                    )
            else:
                agent.write(
                    {
                        "is_active": False,
                        "status": "stopped",
                        "process_pid": 0,
                        "last_stopped": fields.Datetime.now(),
                    }
                )

    def unlink(self):
        for record in self:
            if record.is_active:
                try:
                    record._action_stop_one()
                except Exception as e:
                    _logger.warning("Failed to stop agent %s before unlink: %s", record.id, e)
        return super().unlink()

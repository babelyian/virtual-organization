from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_agno_bot = fields.Boolean(
        string="Is Agno Bot",
        default=False,
        help="Mark this user as an Agno Agent bot. When added to a Discuss channel, it will automatically reply to messages via the linked agent."
    )
    agno_agent_name = fields.Char(
        string="Agent Name/Code",
        help="The agent identifier used in the API URL, e.g. 'trino-agent'"
    )
    agno_agent_base_url = fields.Char(
        string="Agent API Base URL",
        default="http://localhost:7777",
        help="Base URL of the Agno agent server (without /agents/...)"
    )
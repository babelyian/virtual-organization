from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = "res.users"

    is_agno_bot = fields.Boolean(default=False)

    agno_agent_id = fields.Many2one(
        "agno.agent",
        string="Linked Agent",
        domain=[("status", "=", "running")],
        help="Select which Agno Agent this bot user should use",
    )

    agno_agent_name = fields.Char(
        related="agno_agent_id.agent_name",
        readonly=True,
        store=True,
    )

    agno_agent_base_url = fields.Char(
        related="agno_agent_id.host",
        readonly=True,
        store=True,
    )
    agno_agent_port = fields.Integer(
        related="agno_agent_id.port",
        readonly=True,
        store=True,
    )

    @api.onchange("is_agno_bot")
    def _onchange_is_agno_bot(self):
        if not self.is_agno_bot:
            self.agno_agent_id = False

    @api.constrains("is_agno_bot", "agno_agent_id")
    def _check_bot_has_agent(self):
        for rec in self:
            if rec.is_agno_bot and not rec.agno_agent_id:
                raise ValidationError(_("Agno Bot users must have a Linked Agno Agent."))

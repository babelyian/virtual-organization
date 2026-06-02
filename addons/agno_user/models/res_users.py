from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    is_agno_bot = fields.Boolean(default=False)

    # Change to Reference field to allow both models
    agno_agent_id = fields.Reference(
        selection=[
            ('agno.agent', 'Agno Agent'),
            ('agno.current.activity.report', 'Activity Report Agent'),
        ],
        string="Linked Agent",
        # domain="[('status', '=', 'running')]",
        help="Select which Agno Agent this bot user should use",
    )

    # For displaying agent name (works with both models)
    agno_agent_name = fields.Char(
        compute='_compute_agent_info',
        store=False,
    )

    agno_agent_base_url = fields.Char(
        compute='_compute_agent_info',
        store=False,
    )

    agno_agent_port = fields.Integer(
        compute='_compute_agent_info',
        store=False,
    )

    def _compute_agent_info(self):
        for rec in self:
            agent = rec.agno_agent_id
            if agent:
                rec.agno_agent_name = agent.agent_name
                rec.agno_agent_base_url = agent.host
                rec.agno_agent_port = agent.port
            else:
                rec.agno_agent_name = False
                rec.agno_agent_base_url = False
                rec.agno_agent_port = False

    @api.onchange("is_agno_bot")
    def _onchange_is_agno_bot(self):
        if not self.is_agno_bot:
            self.agno_agent_id = False

    @api.constrains("is_agno_bot", "agno_agent_id")
    def _check_bot_has_agent(self):
        for rec in self:
            if rec.is_agno_bot and not rec.agno_agent_id:
                raise ValidationError(_("Agno Bot users must have a Linked Agno Agent."))
import requests
import logging
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    is_agno_bot_channel = fields.Boolean(
        string="Agno Agent Channel",
        default=False,
        help="Mark this channel as connected to an external Agno Agent"
    )
    agno_agent_name = fields.Char(
        string="Agent Name/Code",
        help="The agent identifier used in URL, e.g. 'trino-agent'"
    )
    agno_agent_base_url = fields.Char(
        string="Agent API Base URL",
        default="http://localhost:7777",
        help="Base URL of the Agno agent server (without /agents/...)"
    )
    agno_session_id = fields.Char(
        string="Agent Session ID",
        copy=False,
        help="Persistent session identifier for this conversation"
    )

    @api.model_create_multi
    def create(self, vals_list):
        channels = super().create(vals_list)
        for channel in channels:
            if channel.is_agno_bot_channel and not channel.agno_session_id:
                channel.agno_session_id = (
                    f"odoo_chat_{channel.id}_{self.env.uid}_"
                    f"{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"
                )
        return channels

    def _get_agent_full_url(self):
        self.ensure_one()
        if not self.agno_agent_name or not self.agno_agent_base_url:
            raise UserError(_("Missing agent name or base URL configuration"))
        return f"{self.agno_agent_base_url.rstrip('/')}/agents/{self.agno_agent_name}/runs"

    def message_post(self, *, parent_id=False, subtype_xmlid=False, **kwargs):
        if self.env.context.get('agno_bot_reply'):
            return super().message_post(parent_id=parent_id, subtype_xmlid=subtype_xmlid, **kwargs)

        message = super().message_post(parent_id=parent_id, subtype_xmlid=subtype_xmlid, **kwargs)

        if not self.is_agno_bot_channel:
            return message

        self.with_context(mail_post_autofollow=False)._send_to_agno_agent(kwargs.get('body', ''))

        return message

    def _send_to_agno_agent(self, user_message):
        self.ensure_one()

        url = self._get_agent_full_url()
        payload = {
            'message': user_message.strip(),
            'session_id': self.agno_session_id,
        }

        _logger.info("Sending to Agno agent [%s] → %s", self.name, user_message[:80])

        try:
            response = requests.post(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=90,
                stream=False,
            )
            response.raise_for_status()
            data = response.json()

            content = data.get('content', '').strip()
            status = data.get('status', '')

            if status == 'COMPLETED' and content:
                self._post_bot_reply(content)
            else:
                self._post_bot_reply("Agent is still thinking… (status: %s)" % status)

        except Exception as e:
            _logger.error("Agno agent error: %s", str(e))
            self._post_bot_reply(f"Error: {str(e)}", is_error=True)

    def _post_bot_reply(self, body, message_type='comment', is_error=False):

        bot_partner = self.env.ref('agno_discuss_bot.partner_agno_bot')

        body = body.strip()
        if not body:
            return 

        if is_error:
            body = f'<span style="color:#e74c3c;"><strong>Error from Agent:</strong> {body}</span>'

        try:
            self.sudo().with_context(agno_bot_reply=True).message_post(
                author_id=bot_partner.id,
                body=body,
                message_type=message_type,
                subtype_xmlid='mail.mt_comment',

            )
        except Exception as e:
            _logger.error("Failed to post bot reply: %s", str(e), exc_info=True)
            self.sudo().message_post(
                author_id=bot_partner.id,
                body=f"[Bot Error] Could not post reply: {str(e)}",
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
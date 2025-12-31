import requests
import logging
import json
from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def message_post(self, *, parent_id=False, subtype_xmlid=False, **kwargs):
        if self.env.context.get('agno_bot_reply'):
            return super().message_post(parent_id=parent_id, subtype_xmlid=subtype_xmlid, **kwargs)

        message = super().message_post(parent_id=parent_id, subtype_xmlid=subtype_xmlid, **kwargs)

        bot_users = self.channel_member_ids.mapped('partner_id.user_ids').filtered(lambda u: u.is_agno_bot)
        if not bot_users:
            return message

        bot_user = bot_users[0]

        if message.author_id.user_ids and message.author_id.user_ids.is_agno_bot:
            return message

        self.with_context(agno_bot_reply_user=bot_user)._send_to_agno_agent(kwargs.get('body', ''), bot_user)

        return message

    def _send_to_agno_agent(self, user_message, bot_user):
        self.ensure_one()

        url = f"{bot_user.agno_agent_base_url.rstrip('/')}/agents/{bot_user.agno_agent_name}/runs"
        session_id = f"odoo_chat_{self.uuid}" 

        payload = {
            'message': user_message.strip(),
            'session_id': session_id,
            # 'stream': 'True',  # Uncomment if your agent supports streaming
        }

        _logger.info("Sending to Agno agent [%s] from bot [%s] → %s", self.name, bot_user.name, user_message[:80])

        try:
            response = requests.post(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=90,
                stream=False,
            )
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError:
                _logger.warning("Agno agent returned non-JSON response")
                self._post_bot_reply(_("Agent returned invalid response format."), bot_user, is_error=True)
                return

            content = data.get('content', '').strip()
            status = data.get('status', 'UNKNOWN')

            if status == 'COMPLETED' and content:
                self._post_bot_reply(content, bot_user)
            elif status in ('ERROR', 'FAILED'):
                error_msg = data.get('error', data.get('reasoning_content', 'Unknown error'))
                self._post_bot_reply(f"**Agent Error**: {error_msg}", bot_user, is_error=True)
            else:
                msg = f"**Agent response** (status: {status})\n\n{content}"
                if 'reasoning_content' in data:
                    msg += f"\n\n**Reasoning**:\n{data['reasoning_content']}"
                self._post_bot_reply(msg, bot_user)

        except requests.exceptions.RequestException as e:
            _logger.error("Agno agent communication failed: %s", str(e))
            error_text = str(e)
            if "Connection refused" in error_text:
                error_text = "Cannot connect to agent server. Is it running?"
            self._post_bot_reply(
                f"**Connection Error** with {bot_user.agno_agent_name}:\n{error_text}",
                bot_user,
                is_error=True
            )

    def _post_bot_reply(self, body, bot_user, message_type='comment', is_error=False):
        bot_partner = bot_user.partner_id

        body = body.strip()
        if not body:
            return

        if is_error:
            body = f'<span style="color:#e74c3c;"><strong>Agent Error:</strong> {body}</span>'

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
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
            'stream': 'True',
        }

        _logger.info("Sending to Agno agent [%s] from bot [%s] → %s", self.name, bot_user.name, user_message[:80])

        try:
            response = requests.post(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=120,
                stream=True,
            )
            response.raise_for_status()

            full_content = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    _logger.debug("SSE line: %s", decoded_line)

                    if decoded_line.startswith('data: '):
                        data_str = decoded_line[6:].strip()
                        try:
                            event_data = json.loads(data_str)
                            # Accumulate content from RunContent events
                            if event_data.get('event') == 'RunContent':
                                full_content += event_data.get('content', '')
                            # Check for final completion
                            elif event_data.get('event') == 'RunCompleted':
                                full_content = event_data.get('content', full_content).strip()
                                break
                        except json.JSONDecodeError:
                            _logger.debug("Non-JSON SSE data: %s", data_str)
                            full_content += data_str + "\n"

            if full_content:
                self._post_bot_reply(full_content, bot_user)
            else:
                self._post_bot_reply("Agent returned empty response.", bot_user, is_error=True)

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
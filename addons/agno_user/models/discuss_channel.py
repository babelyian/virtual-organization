import re
import json
import logging
import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MENTION_RE = re.compile(r"^\s*@([^\s]+)\s*(.*)$", re.S)

def _strip_html(s: str) -> str:
    s = s or ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ")
    return s.strip()

def _norm_key(s: str) -> str:
    s = (s or "").strip().lower()
    return re.sub(r"[\s_\-]+", "", s)


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def message_post(self, *, parent_id=False, subtype_xmlid=False, **kwargs):
        if self.env.context.get("agno_bot_reply"):
            return super().message_post(parent_id=parent_id, subtype_xmlid=subtype_xmlid, **kwargs)

        message = super().message_post(parent_id=parent_id, subtype_xmlid=subtype_xmlid, **kwargs)

        bot_users = self.channel_member_ids.mapped("partner_id.user_ids").filtered(
            lambda u: u.is_agno_bot and u.agno_agent_id
        )
        if not bot_users:
            return message

        body_raw = message.body or kwargs.get("body", "") or ""
        bot_user, cleaned_text = self._pick_bot_and_clean_message(bot_users, body_raw)

        if message.author_id == bot_user.partner_id:
            return message

        ctx = {"agno_bot_reply": True, "agno_bot_reply_user": bot_user}
        self.with_context(**ctx)._send_to_agno_agent(cleaned_text, bot_user)

        return message

    def _pick_bot_and_clean_message(self, bot_users, body_raw):
        text = _strip_html(body_raw)
        m = MENTION_RE.match(text)
        if not m:
            return bot_users[0], text

        mention = _norm_key(m.group(1))
        rest = (m.group(2) or "").strip()

        for u in bot_users:
            candidates = [
                u.login,
                u.name,
                u.partner_id.name,
                u.agno_agent_id.agent_name,
            ]
            if any(_norm_key(c) == mention for c in candidates if c):
                return u, (rest or text)

        return bot_users[0], text


    def _send_to_agno_agent(self, user_message, bot_user):
        self.ensure_one()

        agent = bot_user.agno_agent_id
        if not agent:
            raise UserError(_("This bot user has no linked agent."))

        host = agent.host or "127.0.0.1"
        if host == "0.0.0.0":
            host = "127.0.0.1"

        url = f"http://{host}:{agent.port}/agents/{agent.agent_name}/runs"
        session_id = f"odoo_chat_{self.uuid}"

        payload = {
            "message": (user_message or "").strip(),
            "session_id": session_id,
            "stream": True,
        }

        _logger.info(
            "Sending to Agno agent [%s:%s/%s] from bot [%s] → %s",
            host, agent.port, agent.agent_name, bot_user.name, (user_message or "")[:80]
        )

        try:
            response = requests.post(
                url,
                data=payload,  
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=120,
                stream=True,
            )
            response.raise_for_status()

            full_content = ""
            for line in response.iter_lines():
                if not line:
                    continue

                decoded_line = line.decode("utf-8", errors="ignore").strip()
                _logger.debug("SSE line: %s", decoded_line)

                if not decoded_line.startswith("data:"):
                    continue

                data_str = decoded_line[5:].strip()
                try:
                    event_data = json.loads(data_str)
                    if event_data.get("event") == "RunContent":
                        full_content += event_data.get("content", "")
                    elif event_data.get("event") == "RunCompleted":
                        full_content = (event_data.get("content") or full_content).strip()
                        break
                except json.JSONDecodeError:
                    # fallback: treat it as raw chunk
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
                f"**Connection Error** with {agent.agent_name}:\n{error_text}",
                bot_user,
                is_error=True,
            )

    def _post_bot_reply(self, body, bot_user, message_type="comment", is_error=False):
 
        bot_partner = bot_user.partner_id
        body = (body or "").strip()
        if not body:
            return

        if is_error:
            body = f'<span style="color:#e74c3c;"><strong>Agent Error:</strong> {body}</span>'

        self.sudo().with_context(agno_bot_reply=True).message_post(
            author_id=bot_partner.id,
            body=body,
            message_type=message_type,
            subtype_xmlid="mail.mt_comment",
        )

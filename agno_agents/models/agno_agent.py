import logging
import uuid
import html
from odoo.tools import plaintext2html

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from trino.dbapi import connect


_logger = logging.getLogger(__name__)

class AgnoAgent(models.Model):
    _name = "agno.agent"
    _description = "Agno Agent Configuration"
    _rec_name = "agent_name"
    _inherit = []

    agent_name = fields.Char("Agent Name", required=True, help="Name of the Agno agent")
    agent_role = fields.Text("Agent Role", required=True, help="Description of the agent's role and capabilities")
    instructions = fields.Text("Instructions", help="Additional instructions for the agent")
    model_name = fields.Selection([
        ('gpt-oss:20b', 'GPT-OSS 20B'),
        ('Qwen3-Instruct:30b', 'Qwen3-Instruct 30B'),
        ('gemma-3:27b', 'Gemma-3 27B'),
    ], string='Model', required=True, default='gemma-3:27b')
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
    
    trino_host = fields.Char("Trino Host", default="10.20.30.170")
    trino_port = fields.Integer("Trino Port", default=8082)
    trino_user = fields.Char("Trino User", default="trino")
    trino_catalog = fields.Char("Trino Catalog", default="hive")
    trino_schema = fields.Char("Trino Schema", default="contest")
    trino_table = fields.Char("Trino Table", default="chunks")

    @api.constrains("agent_name")
    def _check_agent_name(self):
        for rec in self:
            if not rec.agent_name or not rec.agent_name.strip():
                raise ValidationError(_("Agent name cannot be empty"))

    @api.constrains("trino_port")
    def _check_trino_port(self):
        for rec in self:
            if rec.trino_port and (rec.trino_port < 1 or rec.trino_port > 65535):
                raise ValidationError(_("Trino port must be between 1 and 65535"))

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

    @api.model
    def _get_or_create_notify_channel(self, channel_name="smart-bucket"):

        admin = self.env.ref("base.user_admin", raise_if_not_found=False) or self.env["res.users"].sudo().browse(1)
        admin_partner = admin.partner_id

        Channel = self.env["discuss.channel"].sudo()

        channel = Channel.search([("name", "=", channel_name)], limit=1)

        if not channel:
            vals = {
                "name": channel_name,
            }
            channel = Channel.create(vals)

        if admin_partner and admin_partner.id not in channel.channel_partner_ids.ids:
            channel.write({"channel_partner_ids": [(4, admin_partner.id)]})

        return channel

    def _to_html(self, text: str) -> str:
        safe = html.escape(text or "")
        return safe.replace("\n", "<br/>")

    @api.model
    def _post_to_notify_channel(self, subject: str, body: str, channel_name="agno-cron"):
        channel = self._get_or_create_notify_channel(channel_name=channel_name)

        safe_subject = (subject or "").strip()

        safe_body_html = plaintext2html(body or "")

        channel.message_post(
            subject=safe_subject,
            body=safe_body_html,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        return True

    def _get_trino_conn(self):
        self.ensure_one()

        if not self.trino_host or not self.trino_catalog or not self.trino_schema:
            raise UserError(
                _("Trino config incomplete for agent '%s'") % (self.agent_name)
            )

        return connect(
            host=self.trino_host,
            port=int(self.trino_port or 8082),
            user=self.trino_user or "trino",
            catalog=self.trino_catalog,
            schema=self.trino_schema,
            http_scheme="http",
        )

    def _fetch_standardized_chunks(self, limit: int = 5):
        self.ensure_one()

        if not self.trino_table:
            raise UserError(
                _("Trino table not configured for agent '%s'") % self.agent_name
            )

        sql = f"""
            SELECT standardized_chunk
            FROM {self.trino_table}
            LIMIT {int(limit)}
        """

        conn = None
        try:
            conn = self._get_trino_conn()
            cur = conn.cursor()
            cur.execute(sql)

            rows = cur.fetchall()
            return [r[0] for r in rows if r and r[0]]

        except Exception as e:
            _logger.exception("Trino query failed for agent %s", self.agent_name)
            raise UserError(_("Trino query failed: %s") % e)

        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    @api.model
    def cron_broadcast_prompt_to_active_agents(self):

        ICP = self.env["ir.config_parameter"].sudo()
        base_prompt = (ICP.get_param("agno.cron.prompt") or "Provide me a summary of the input text based on your role.").strip()
        channel_name = (ICP.get_param("agno.cron.notify_channel") or "smart-bucket").strip()
        chunk_limit = int(ICP.get_param("agno.cron.trino_chunk_limit") or 5)

        agents = self.search([("is_active", "=", True)])

        if not agents:
            self._post_to_notify_channel(
                subject="Agno Cron Broadcast",
                body=f"Prompt: {base_prompt}\nNo active agents.",
                channel_name=channel_name,
            )
            return True

        action = self.env["agno.action"]

        results = []

        for agent in agents:
            try:
                if agent.status != "running":
                    raise UserError(_("Agent not running"))

                chunks = agent._fetch_standardized_chunks(limit=chunk_limit)

                if chunks:
                    context = "\n\n".join(
                        f"[chunk {i+1}]\n{c}" for i, c in enumerate(chunks)
                    )

                    prompt = f"""
                        {base_prompt}
                        {context}
                    """
                else:
                    prompt = base_prompt

                session_id = f"odoo_cron_{uuid.uuid4().hex[:10]}"
                reply = action.run_prompt(agent, prompt, session_id=session_id)

                results.append(
                    {
                        "agent": agent.agent_name,
                        "ok": True,
                        "chunks": len(chunks),
                        "text": reply or "",
                    }
                )

            except Exception as e:
                _logger.exception(
                    "Cron broadcast failed for agent id=%s name=%s",
                    agent.id,
                    agent.agent_name,
                )

                results.append(
                    {
                        "agent": agent.agent_name,
                        "ok": False,
                        "chunks": 0,
                        "text": str(e),
                    }
                )

        ok_count = sum(r["ok"] for r in results)
        fail_count = len(results) - ok_count

        lines = [
            f"Prompt: {base_prompt}",
            f"Chunks per agent: {chunk_limit}",
            f"Total: {len(results)} | OK: {ok_count} | Failed: {fail_count}",
            "",
        ]

        for r in results:
            status = "OK" if r["ok"] else "ERROR"
            preview = (r["text"] or "").replace("\n", " ")
            lines.append(
                f"{status} {r['agent']} (chunks={r['chunks']}): {preview}"
            )

        subject = (
            "Agno Cron Broadcast (Some Failed)"
            if fail_count
            else "Agno Cron Broadcast (All OK)"
        )

        self._post_to_notify_channel(
            subject=subject,
            body="\n".join(lines),
            channel_name=channel_name,
        )

        return True


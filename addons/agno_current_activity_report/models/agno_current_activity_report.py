import logging
import uuid
import html
from odoo.tools import plaintext2html

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from trino.dbapi import connect


_logger = logging.getLogger(__name__)

class AgnoAgent(models.Model):
    _name = "agno.current.activity.report"
    _inherit = ['agno.agent']
    _description = "Agno Current Activity Report"
    _rec_name = "agent_name"

    external_service_url = fields.Char(
        string="External Service URL",
        default="http://host.docker.internal:8000",
        help="URL of the external agent service (Django/FastAPI)"
    )


    external_agent_id = fields.Char(
        string="External Agent ID",
        help="Agent identifier in the external service"
    )

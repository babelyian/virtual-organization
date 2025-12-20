import os
import subprocess
import time

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AgnoAgent(models.Model):
    _name = 'agno.agent'
    _description = 'Agno Agent Configuration'
    _rec_name = 'agent_name'
    # Removed mail.thread + mail.activity.mixin
    _inherit = []

    # Basic agent properties
    agent_name = fields.Char('Agent Name', required=True, help="Name of the Agno agent")
    agent_role = fields.Text(
        'Agent Role',
        required=True,
        help="Description of the agent's role and capabilities"
    )
    instructions = fields.Text('Instructions', help="Additional instructions for the agent")

    # Model configuration
    model_id = fields.Char(
        'Model ID',
        required=True,
        default="qwen3:latest",
        help="AI model identifier (e.g., qwen3:latest)"
    )
    base_url = fields.Char(
        'Base URL',
        required=True,
        default="https://chat.aiahura.com/api/v1",
        help="API base URL for the model"
    )
    api_key_env = fields.Char(
        'API Key Environment Variable',
        default="API_KEY",
        help="Environment variable name containing the API key"
    )

    # Agent settings
    add_history_to_context = fields.Boolean('Add History to Context', default=True)
    add_datetime_to_context = fields.Boolean('Add Datetime to Context', default=False)
    markdown = fields.Boolean('Enable Markdown', default=True)
    debug_mode = fields.Boolean('Debug Mode', default=False)
    num_history_runs = fields.Integer('Number of History Runs', default=5)

    # Database settings
    db_file = fields.Char('Database File', default="agent.db", help="SQLite database file name")

    # Status and control
    is_active = fields.Boolean('Active', default=False)
    status = fields.Selection(
        [
            ('stopped', 'Stopped'),
            ('starting', 'Starting'),
            ('running', 'Running'),
            ('stopping', 'Stopping'),
            ('error', 'Error'),
        ],
        default='stopped',
        string='Status',
    )

    port = fields.Integer('Port', default=7777, help="Port where agent will be accessible")
    host = fields.Char('Host', default="0.0.0.0", help="Host address")

    # Error handling
    error_message = fields.Text('Error Message', readonly=True)
    last_started = fields.Datetime('Last Started', readonly=True)
    last_stopped = fields.Datetime('Last Stopped', readonly=True)

    process_pid = fields.Integer('Process PID', readonly=True)

    @api.constrains('agent_name')
    def _check_agent_name(self):
        for record in self:
            if not record.agent_name or not record.agent_name.strip():
                raise ValidationError(_("Agent name cannot be empty"))

    @api.constrains('port')
    def _check_port(self):
        for record in self:
            if record.port < 1 or record.port > 65535:
                raise ValidationError(_("Port must be between 1 and 65535"))

    def action_start_agent(self):
        """Start the Agno agent"""
        self.ensure_one()

        if self.is_active:
            raise UserError(_("Agent is already active"))

        # Check if API key environment variable is set (from Odoo server environment)
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise UserError(_(
                f"API key environment variable '{self.api_key_env}' is not set. "
                f"Please set it in your Odoo service/container environment."
            ))

        try:
            self.status = 'starting'
            self.error_message = False

            script_content = self._generate_agent_script()
            script_path = f"/tmp/agno_agent_{self.id}.py"

            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            process = subprocess.Popen(
                ['python', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )

            time.sleep(2)

            if process.poll() is None:
                self.write({
                    'is_active': True,
                    'status': 'running',
                    'process_pid': process.pid,
                    'last_started': fields.Datetime.now(),
                    'error_message': False
                })
            else:
                stdout, stderr = process.communicate()
                error_msg = (stderr or stdout or b"").decode(errors="replace")
                self.write({
                    'status': 'error',
                    'error_message': f"Failed to start agent: {error_msg}"
                })
                raise UserError(_(f"Failed to start agent: {error_msg}"))

        except Exception as e:
            self.write({
                'status': 'error',
                'error_message': str(e)
            })
            raise UserError(_(f"Error starting agent: {str(e)}"))

    def action_stop_agent(self):
        """Stop the Agno agent"""
        self.ensure_one()

        if not self.is_active:
            raise UserError(_("Agent is not active"))

        try:
            self.status = 'stopping'

            if self.process_pid:
                try:
                    os.killpg(os.getpgid(self.process_pid), 15)  # SIGTERM
                    time.sleep(2)
                    try:
                        os.killpg(os.getpgid(self.process_pid), 9)  # SIGKILL
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    pass

            self.write({
                'is_active': False,
                'status': 'stopped',
                'process_pid': 0,
                'last_stopped': fields.Datetime.now(),
                'error_message': False
            })

        except Exception as e:
            self.write({
                'status': 'error',
                'error_message': str(e)
            })
            raise UserError(_(f"Error stopping agent: {str(e)}"))

    def _generate_agent_script(self):
        """Generate the Python script to run the Agno agent"""
        script = f'''
import os
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb

os.environ.setdefault("AGNO_TELEMETRY", "false")

API_KEY = os.environ.get("{self.api_key_env}")
if API_KEY is None:
    raise RuntimeError("Please set {self.api_key_env} in your environment")

model = OpenAILike(
    id="{self.model_id}",
    base_url="{self.base_url}",
    api_key=API_KEY,
)

db = SqliteDb(db_file="{self.db_file}")

agent = Agent(
    name="{self.agent_name}",
    role="""{self.agent_role}""",
    model=model,
    instructions="""{self.instructions or ''}""",
    db=db,
    add_history_to_context={self.add_history_to_context},
    add_datetime_to_context={self.add_datetime_to_context},
    markdown={self.markdown},
    debug_mode={self.debug_mode},
    num_history_runs={self.num_history_runs},
)

agent_os = AgentOS(agents=[agent])
app = agent_os.get_app()

if __name__ == "__main__":
    print(f"Starting Agent '{{agent.name}}' on http://{self.host}:{self.port}")
    agent_os.serve(app=app, host="{self.host}", port={self.port}, reload=False)
'''
        return script

    @api.model
    def check_agent_status(self):
        """Check and update status of all active agents"""
        active_agents = self.search([('is_active', '=', True)])

        for agent in active_agents:
            if agent.process_pid:
                try:
                    os.kill(agent.process_pid, 0)
                except OSError:
                    agent.write({
                        'is_active': False,
                        'status': 'stopped',
                        'process_pid': 0,
                        'last_stopped': fields.Datetime.now()
                    })

    def unlink(self):
        for record in self:
            if record.is_active:
                record.action_stop_agent()
        return super().unlink()

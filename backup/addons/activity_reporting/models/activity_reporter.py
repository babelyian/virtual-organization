# -*- coding: utf-8 -*-
import logging
import os

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ActivityReporter(models.Model):
    """
    Main model for managing the multi-agent activity reporting system.
    This creates and manages the orchestrator and specialized subagents.
    """
    _name = "activity.reporter"
    _description = "Activity Reporter Configuration"
    _rec_name = "name"

    name = fields.Char("Reporter Name", required=True, default="Activity Reporter")
    
    # Orchestrator Agent
    orchestrator_agent_id = fields.Many2one(
        "agno.agent",
        string="Orchestrator Agent",
        help="Main agent that coordinates subagents"
    )
    
    # Subagents
    employee_agent_id = fields.Many2one(
        "agno.agent",
        string="Employee Agent",
        help="Agent specialized in employee data"
    )
    
    todo_agent_id = fields.Many2one(
        "agno.agent",
        string="Todo Agent",
        help="Agent specialized in todo tasks"
    )
    
    project_agent_id = fields.Many2one(
        "agno.agent",
        string="Project Agent",
        help="Agent specialized in project management"
    )
    
    timesheet_agent_id = fields.Many2one(
        "agno.agent",
        string="Timesheet Agent",
        help="Agent specialized in timesheet analysis"
    )
    
    calendar_agent_id = fields.Many2one(
        "agno.agent",
        string="Calendar Agent",
        help="Agent specialized in calendar events"
    )
    
    # Configuration
    base_url = fields.Char(
        "API Base URL",
        required=True,
        default="https://chat.aiahura.com/api/v1",
        help="Base URL for the LLM API"
    )
    
    api_key = fields.Char(
        "API Key",
        required=True,
        help="API key for LLM access"
    )
    
    model_name = fields.Selection([
        ('gpt-oss:20b', 'GPT-OSS 20B'),
        ('Qwen3-Instruct:30b', 'Qwen3-Instruct 30B'),
        ('gemma-3:27b', 'Gemma-3 27B'),
    ], string='LLM Model', required=True, default='gemma-3:27b')
    
    base_port = fields.Integer(
        "Base Port",
        default=8000,
        help="Starting port number for agents (will use base_port, base_port+1, etc.)"
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('configured', 'Configured'),
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    ], default='draft', string='Status')
    
    error_message = fields.Text("Error Message", readonly=True)
    
    # Bot User
    bot_user_id = fields.Many2one(
        "res.users",
        string="Bot User",
        domain=[("is_agno_bot", "=", True)],
        help="Odoo bot user linked to the orchestrator agent"
    )
    
    @api.constrains("base_port")
    def _check_base_port(self):
        for rec in self:
            if rec.base_port < 1024 or rec.base_port > 65529:
                raise ValidationError(_("Base port must be between 1024 and 65529"))
    
    def action_create_agents(self):
        """Create all agents for the activity reporting system"""
        self.ensure_one()
        
        if self.orchestrator_agent_id:
            raise ValidationError(_("Agents already created for this reporter"))
        
        try:
            # Create orchestrator agent
            orchestrator = self._create_orchestrator_agent()
            
            # Create subagents
            employee = self._create_employee_agent()
            todo = self._create_todo_agent()
            project = self._create_project_agent()
            timesheet = self._create_timesheet_agent()
            calendar = self._create_calendar_agent()
            
            self.write({
                'orchestrator_agent_id': orchestrator.id,
                'employee_agent_id': employee.id,
                'todo_agent_id': todo.id,
                'project_agent_id': project.id,
                'timesheet_agent_id': timesheet.id,
                'calendar_agent_id': calendar.id,
                'state': 'configured',
                'error_message': False,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All agents created successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.exception("Failed to create agents")
            self.write({
                'state': 'error',
                'error_message': str(e),
            })
            raise ValidationError(_("Failed to create agents: %s") % str(e))
    
    def action_start_agents(self):
        """Start all agents"""
        self.ensure_one()
        
        if self.state != 'configured' and self.state != 'stopped':
            raise ValidationError(_("Agents must be configured before starting"))
        
        try:
            from ..services.activity_agent_service import ActivityAgentService
            action_model = self.env["agno.action"]
            
            # Start subagents first with enhanced runner
            agent_configs = [
                (self.employee_agent_id, "employee"),
                (self.todo_agent_id, "todo"),
                (self.project_agent_id, "project"),
                (self.timesheet_agent_id, "timesheet"),
                (self.calendar_agent_id, "calendar"),
            ]
            
            for agent, agent_type in agent_configs:
                if agent and not agent.is_active:
                    _logger.info(f"Starting {agent_type} agent...")
                    pid = ActivityAgentService.start_enhanced_agent(agent, agent_type)
                    agent.write({
                        "is_active": True,
                        "status": "running",
                        "process_pid": pid,
                        "last_started": fields.Datetime.now(),
                        "error_message": False,
                    })
            
            # Start orchestrator last with enhanced runner
            if self.orchestrator_agent_id and not self.orchestrator_agent_id.is_active:
                _logger.info("Starting orchestrator agent...")
                pid = ActivityAgentService.start_enhanced_agent(
                    self.orchestrator_agent_id,
                    "orchestrator",
                    base_port=self.base_port
                )
                self.orchestrator_agent_id.write({
                    "is_active": True,
                    "status": "running",
                    "process_pid": pid,
                    "last_started": fields.Datetime.now(),
                    "error_message": False,
                })
            
            self.write({
                'state': 'running',
                'error_message': False,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All agents started successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.exception("Failed to start agents")
            self.write({
                'state': 'error',
                'error_message': str(e),
            })
            raise ValidationError(_("Failed to start agents: %s") % str(e))
    
    def action_stop_agents(self):
        """Stop all agents"""
        self.ensure_one()
        
        try:
            action_model = self.env["agno.action"]
            
            # Stop orchestrator first
            if self.orchestrator_agent_id and self.orchestrator_agent_id.is_active:
                action_model.stop_agents(self.orchestrator_agent_id)
            
            # Stop subagents
            agents = [
                self.employee_agent_id,
                self.todo_agent_id,
                self.project_agent_id,
                self.timesheet_agent_id,
                self.calendar_agent_id,
            ]
            
            for agent in agents:
                if agent and agent.is_active:
                    action_model.stop_agents(agent)
            
            self.write({
                'state': 'stopped',
                'error_message': False,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All agents stopped successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.exception("Failed to stop agents")
            self.write({
                'state': 'error',
                'error_message': str(e),
            })
            raise ValidationError(_("Failed to stop agents: %s") % str(e))
    
    def action_create_bot_user(self):
        """Create a bot user and link it to the orchestrator"""
        self.ensure_one()
        
        if not self.orchestrator_agent_id:
            raise ValidationError(_("Create agents first"))
        
        if self.bot_user_id:
            raise ValidationError(_("Bot user already exists"))
        
        try:
            # Create bot user
            bot_user = self.env["res.users"].create({
                'name': f"{self.name} Bot",
                'login': f"activity_bot_{self.id}",
                'is_agno_bot': True,
                'agno_agent_id': self.orchestrator_agent_id.id,
            })
            
            self.write({
                'bot_user_id': bot_user.id,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Bot user created successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.exception("Failed to create bot user")
            raise ValidationError(_("Failed to create bot user: %s") % str(e))
    
    # Agent creation methods
    
    def _create_orchestrator_agent(self):
        """Create the orchestrator agent"""
        return self.env["agno.agent"].create({
            'agent_name': f"activity_orchestrator_{self.id}",
            'agent_role': """You are an Orchestrator Agent for the Current Activity Reporting system.

You have access to the `call_agent` tool to query specialized agents.

**Available Agents:**
- employee: Employee information and HR data  
- project: Project status and tasks
- timesheet: Time tracking and hours
- calendar: Calendar events and meetings

**How to use call_agent:**
call_agent(agent_type="project", query="List all active projects")
call_agent(agent_type="employee", query="Find employees in Engineering")
call_agent(agent_type="timesheet", query="Show hours logged last week")
call_agent(agent_type="calendar", query="Upcoming meetings")

**Your process:**
1. Understand the user's question
2. Decide which agent(s) to consult
3. Call the appropriate agent(s) with clear queries
4. **IMPORTANT: After receiving tool responses, ALWAYS format and present the information to the user**
5. Combine responses into a helpful, well-formatted answer

CRITICAL: You MUST respond to the user after calling tools. Don't just call tools silently - always explain what you found!

Example:
User: "What projects are we working on?"
You: "Let me check our active projects. [calls call_agent]"
You: "Here are our current projects: [presents the results from call_agent in a clear format]"

IMPORTANT: Always use call_agent to get current data. Never make up information.""",
            'instructions': """When a user asks a question:
1. Immediately call the appropriate agent(s) using call_agent
2. Wait for the response
3. ALWAYS present the response to the user in a clear, formatted way
4. Use markdown formatting (bullet points, headers, bold) to make responses easy to read
5. If calling multiple agents, present each result clearly

NEVER return an empty response. If a tool returns data, you MUST present that data to the user.

Be specific in your queries to agents. Format responses clearly with bullet points.""",
            'model_name': self.model_name,
            'base_url': self.base_url,
            'api_key': self.api_key,
            'port': self.base_port,
            'host': '0.0.0.0',
            'db_file': f'orchestrator_{self.id}.db',
            'add_history_to_context': True,
            'add_datetime_to_context': True,
            'markdown': True,
            'debug_mode': True,  # Enable debug mode
            'num_history_runs': 10,
        })
    
    def _create_employee_agent(self):
        """Create the employee agent"""
        return self.env["agno.agent"].create({
            'agent_name': f"employee_agent_{self.id}",
            'agent_role': """You are an Employee Agent specialized in retrieving employee information from Odoo.

YOU HAVE ACCESS TO THESE TOOLS:

1. search_employees(name=None, department=None, active_only=True, limit=50)
   - Search for employees by name and/or department
   - Returns formatted list of employees with their details
   
2. get_employee_details(employee_name: str)
   - Get detailed information about a specific employee
   - Returns comprehensive employee profile

WHEN TO USE EACH TOOL:

Use search_employees when:
- User asks "list all employees"
- User asks "who works in [department]?"
- User asks "find employees named [name]"
- User asks general questions about employees

Use get_employee_details when:
- User asks about a specific employee by name
- User needs detailed info about one person

EXAMPLES:

Query: "List all active employees"
Action: Call search_employees(active_only=True)

Query: "Who works in Sales department?"
Action: Call search_employees(department="Sales")

Query: "Find employee John Smith"
Action: Call get_employee_details(employee_name="John Smith")

Query: "Show me all employees"
Action: Call search_employees()

ALWAYS use the tools to get real data from Odoo. Never make up employee information.""",
            'instructions': """CRITICAL: You MUST use the search_employees or get_employee_details tools for every query.

Never respond without calling a tool first.
Base all responses on the tool output.
Format the results clearly for the user.""",
            'model_name': self.model_name,
            'base_url': self.base_url,
            'api_key': self.api_key,
            'port': self.base_port + 1,
            'host': '0.0.0.0',
            'db_file': f'employee_{self.id}.db',
            'add_history_to_context': True,
            'markdown': True,
        })
    
    def _create_todo_agent(self):
        """Create the todo agent"""
        return self.env["agno.agent"].create({
            'agent_name': f"todo_agent_{self.id}",
            'agent_role': """You are a Todo Agent specialized in managing and reporting on todo tasks.
            
Your responsibilities:
- Query todo tasks from the system
- Report on task status (open, completed, overdue)
- Provide task details including assignees, deadlines, and priorities
- Summarize todo lists by user, priority, or deadline

When responding:
- Organize tasks logically (by priority, deadline, or assignee)
- Highlight overdue or urgent tasks
- Provide clear status updates
- Include relevant task details""",
            'instructions': """Use Odoo API to query todo tasks.
Pay special attention to deadlines and priorities.
Format task lists clearly with status indicators.""",
            'model_name': self.model_name,
            'base_url': self.base_url,
            'api_key': self.api_key,
            'port': self.base_port + 2,
            'host': '0.0.0.0',
            'db_file': f'todo_{self.id}.db',
            'add_history_to_context': True,
            'markdown': True,
        })
    
    def _create_project_agent(self):
        """Create the project agent"""
        return self.env["agno.agent"].create({
            'agent_name': f"project_agent_{self.id}",
            'agent_role': """You are a Project Agent that queries Odoo for project and task information.

You have tools to:
1. Get all active projects with their details
2. Get tasks for specific projects or all tasks

When users ask about projects or tasks, use your tools to fetch current data from Odoo.
Present the information clearly and helpfully.""",
            'instructions': """Always use your tools to get real data from Odoo.
Format responses with clear sections and bullet points.
Include project names, task counts, and relevant details.""",
            'model_name': self.model_name,
            'base_url': self.base_url,
            'api_key': self.api_key,
            'port': self.base_port + 3,
            'host': '0.0.0.0',
            'db_file': f'project_{self.id}.db',
            'add_history_to_context': True,
            'markdown': True,
        })
    
    def _create_timesheet_agent(self):
        """Create the timesheet agent"""
        return self.env["agno.agent"].create({
            'agent_name': f"timesheet_agent_{self.id}",
            'agent_role': """You are a Timesheet Agent specialized in time tracking and analysis.
            
Your responsibilities:
- Query timesheet entries
- Analyze time spent on projects and tasks
- Report on employee work hours
- Calculate time allocations and utilization
- Identify time tracking patterns and trends

When responding:
- Summarize hours by employee, project, or time period
- Calculate totals and averages
- Show time distribution clearly
- Highlight any unusual patterns or concerns
- Format time data consistently (hours, days, etc.)""",
            'instructions': """Query account.analytic.line (timesheet entries).
Calculate time totals accurately.
Group time data by relevant dimensions (employee, project, date range).""",
            'model_name': self.model_name,
            'base_url': self.base_url,
            'api_key': self.api_key,
            'port': self.base_port + 4,
            'host': '0.0.0.0',
            'db_file': f'timesheet_{self.id}.db',
            'add_history_to_context': True,
            'markdown': True,
        })
    
    def _create_calendar_agent(self):
        """Create the calendar agent"""
        return self.env["agno.agent"].create({
            'agent_name': f"calendar_agent_{self.id}",
            'agent_role': """You are a Calendar Agent specialized in calendar events and scheduling.
            
Your responsibilities:
- Query calendar events and meetings
- Report on upcoming meetings and events
- Provide meeting details (time, participants, location)
- Identify scheduling conflicts
- Summarize daily/weekly schedules

When responding:
- List events chronologically
- Include all relevant meeting details
- Highlight important or urgent meetings
- Show participant information
- Format dates and times clearly""",
            'instructions': """Query calendar.event model.
Pay attention to event dates, times, and attendees.
Format schedules in a clear, easy-to-read format.""",
            'model_name': self.model_name,
            'base_url': self.base_url,
            'api_key': self.api_key,
            'port': self.base_port + 5,
            'host': '0.0.0.0',
            'db_file': f'calendar_{self.id}.db',
            'add_history_to_context': True,
            'markdown': True,
        })

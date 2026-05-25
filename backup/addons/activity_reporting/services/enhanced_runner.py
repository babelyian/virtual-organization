# -*- coding: utf-8 -*-
"""
Enhanced Agent Runner with Tool Integration

This runner provides agents with actual callable tools to:
- Query Odoo data directly (for subagents)
- Call other agents via HTTP (for orchestrator)
"""

import argparse
import json
import os
import sys
import time
import logging
import traceback
import requests
from typing import Dict, Any, List
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb


_logger = logging.getLogger(__name__)


def setup_logging(log_path: str, debug: bool = True):
    """Configure logging"""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ============================================================================
# ODOO DATA ACCESS TOOLS (for subagents)
# ============================================================================

def create_odoo_xmlrpc_tools(odoo_url: str, db: str, username: str, password: str):
    """Create tools that access Odoo via XML-RPC"""
    import xmlrpc.client
    
    common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')
    
    def search_read(model: str, domain: List = None, fields: List = None, limit: int = 80):
        """Search and read records from Odoo"""
        domain = domain or []
        fields = fields or []
        try:
            records = models.execute_kw(
                db, uid, password,
                model, 'search_read',
                [domain],
                {'fields': fields, 'limit': limit}
            )
            return records
        except Exception as e:
            _logger.error(f"Error querying {model}: {e}")
            return []
    
    return search_read


def get_projects(search_read_func) -> str:
    """Get active projects"""
    try:
        projects = search_read_func(
            'project.project',
            [('active', '=', True)],
            ['name', 'task_count', 'user_id'],
            limit=50
        )
        
        if not projects:
            return "No active projects found."
        
        result = f"Found {len(projects)} active projects:\n\n"
        for p in projects:
            result += f"- **{p['name']}** (ID: {p['id']})\n"
            result += f"  Tasks: {p.get('task_count', 0)}\n"
            if p.get('user_id'):
                result += f"  Manager: {p['user_id'][1]}\n"
            result += "\n"
        
        return result
    except Exception as e:
        return f"Error retrieving projects: {str(e)}"


def get_project_tasks(search_read_func, project_name: str = None) -> str:
    """Get tasks, optionally filtered by project"""
    try:
        domain = []
        if project_name:
            # First find the project
            projects = search_read_func(
                'project.project',
                [('name', 'ilike', project_name)],
                ['id', 'name'],
                limit=1
            )
            if projects:
                domain = [('project_id', '=', projects[0]['id'])]
        
        tasks = search_read_func(
            'project.task',
            domain,
            ['name', 'project_id', 'user_ids', 'stage_id', 'date_deadline'],
            limit=50
        )
        
        if not tasks:
            return f"No tasks found{' for project ' + project_name if project_name else ''}."
        
        result = f"Found {len(tasks)} tasks:\n\n"
        for t in tasks:
            result += f"- **{t['name']}**\n"
            if t.get('project_id'):
                result += f"  Project: {t['project_id'][1]}\n"
            if t.get('user_ids'):
                result += f"  Assigned to: {len(t['user_ids'])} user(s)\n"
            if t.get('stage_id'):
                result += f"  Stage: {t['stage_id'][1]}\n"
            if t.get('date_deadline'):
                result += f"  Deadline: {t['date_deadline']}\n"
            result += "\n"
        
        return result
    except Exception as e:
        return f"Error retrieving tasks: {str(e)}"


def get_employees(search_read_func, department: str = None) -> str:
    """Get employees, optionally filtered by department"""
    try:
        domain = [('active', '=', True)]
        if department:
            # Find department first
            depts = search_read_func(
                'hr.department',
                [('name', 'ilike', department)],
                ['id'],
                limit=1
            )
            if depts:
                domain.append(('department_id', '=', depts[0]['id']))
        
        employees = search_read_func(
            'hr.employee',
            domain,
            ['name', 'department_id', 'job_title', 'work_email'],
            limit=50
        )
        
        if not employees:
            return f"No employees found{' in department ' + department if department else ''}."
        
        result = f"Found {len(employees)} employees:\n\n"
        for e in employees:
            result += f"- **{e['name']}**\n"
            if e.get('department_id'):
                result += f"  Department: {e['department_id'][1]}\n"
            if e.get('job_title'):
                result += f"  Position: {e['job_title']}\n"
            result += "\n"
        
        return result
    except Exception as e:
        return f"Error retrieving employees: {str(e)}"


def get_timesheets(search_read_func, employee_name: str = None, project_name: str = None, days: int = 7) -> str:
    """Get timesheet entries"""
    try:
        from datetime import datetime, timedelta
        
        domain = []
        
        # Date filter
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        domain.append(('date', '>=', date_from))
        
        # Employee filter
        if employee_name:
            employees = search_read_func(
                'hr.employee',
                [('name', 'ilike', employee_name)],
                ['id'],
                limit=1
            )
            if employees:
                domain.append(('employee_id', '=', employees[0]['id']))
        
        # Project filter
        if project_name:
            projects = search_read_func(
                'project.project',
                [('name', 'ilike', project_name)],
                ['id'],
                limit=1
            )
            if projects:
                domain.append(('project_id', '=', projects[0]['id']))
        
        timesheets = search_read_func(
            'account.analytic.line',
            domain,
            ['employee_id', 'project_id', 'task_id', 'unit_amount', 'date', 'name'],
            limit=100
        )
        
        if not timesheets:
            return "No timesheet entries found for the specified criteria."
        
        # Calculate totals
        total_hours = sum(t.get('unit_amount', 0) for t in timesheets)
        
        result = f"Found {len(timesheets)} timesheet entries (last {days} days):\n"
        result += f"**Total Hours: {total_hours:.2f}**\n\n"
        
        # Group by employee
        by_employee = {}
        for t in timesheets:
            emp = t.get('employee_id', [None, 'Unknown'])[1]
            if emp not in by_employee:
                by_employee[emp] = []
            by_employee[emp].append(t)
        
        for emp, entries in by_employee.items():
            emp_hours = sum(e.get('unit_amount', 0) for e in entries)
            result += f"- **{emp}**: {emp_hours:.2f} hours ({len(entries)} entries)\n"
        
        return result
    except Exception as e:
        return f"Error retrieving timesheets: {str(e)}"


def get_calendar_events(search_read_func, days_ahead: int = 7) -> str:
    """Get upcoming calendar events"""
    try:
        from datetime import datetime, timedelta
        
        date_from = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_to = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d %H:%M:%S')
        
        events = search_read_func(
            'calendar.event',
            [('start', '>=', date_from), ('start', '<=', date_to)],
            ['name', 'start', 'stop', 'location', 'partner_ids'],
            limit=50
        )
        
        if not events:
            return f"No events scheduled for the next {days_ahead} days."
        
        result = f"Found {len(events)} upcoming events:\n\n"
        for e in events:
            result += f"- **{e['name']}**\n"
            result += f"  Start: {e.get('start', 'N/A')}\n"
            result += f"  End: {e.get('stop', 'N/A')}\n"
            if e.get('location'):
                result += f"  Location: {e['location']}\n"
            if e.get('partner_ids'):
                result += f"  Participants: {len(e['partner_ids'])} people\n"
            result += "\n"
        
        return result
    except Exception as e:
        return f"Error retrieving calendar events: {str(e)}"


# ============================================================================
# AGENT COMMUNICATION TOOLS (for orchestrator)
# ============================================================================

def create_agent_caller(base_port: int, orchestrator_name: str = ""):
    """Create a function that can call other agents via HTTP"""
    
    # Extract reporter ID from orchestrator name (e.g., "activity_orchestrator_1" -> "1")
    reporter_id = orchestrator_name.split("_")[-1] if "_" in orchestrator_name else "1"
    
    def call_agent(agent_type: str, query: str) -> str:
        """
        Call a specialized agent with a query
        
        Args:
            agent_type: One of 'employee', 'todo', 'project', 'timesheet', 'calendar'
            query: The question to ask the agent
            
        Returns:
            The agent's response
        """
        _logger.info(f"Orchestrator calling {agent_type} agent with query: {query}")
        
        port_map = {
            'employee': base_port + 1,
            'todo': base_port + 2,
            'project': base_port + 3,
            'timesheet': base_port + 4,
            'calendar': base_port + 5,
        }
        
        port = port_map.get(agent_type.lower())
        if not port:
            error_msg = f"Unknown agent type: {agent_type}. Valid types: {', '.join(port_map.keys())}"
            _logger.error(error_msg)
            return error_msg
        
        # Agent name includes reporter ID
        agent_name = f"{agent_type.lower()}_agent_{reporter_id}"
        url = f"http://127.0.0.1:{port}/agents/{agent_name}/runs"
        
        _logger.info(f"Calling URL: {url}")
        
        try:
            response = requests.post(
                url,
                data={
                    'message': query,
                    'session_id': f'orchestrator_{int(time.time())}',
                    'stream': False
                },
                timeout=60
            )
            response.raise_for_status()
            
            # Parse response
            content = ""
            for line in response.iter_lines():
                if not line:
                    continue
                decoded = line.decode('utf-8', errors='ignore').strip()
                if decoded.startswith('data:'):
                    data_str = decoded[5:].strip()
                    try:
                        event_data = json.loads(data_str)
                        if event_data.get('event') == 'RunContent':
                            content += event_data.get('content', '')
                        elif event_data.get('event') == 'RunCompleted':
                            content = event_data.get('content', content).strip()
                            break
                    except json.JSONDecodeError:
                        content += data_str
            
            result = content.strip() or "Agent returned no response"
            _logger.info(f"{agent_type} agent response: {result[:200]}...")
            return result
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Cannot connect to {agent_type} agent (port {port}). Is it running?"
            _logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error calling {agent_type} agent: {str(e)}"
            _logger.error(error_msg)
            return error_msg
    
    return call_agent


# ============================================================================
# MAIN RUNNER
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to JSON config")
    args = parser.parse_args()
    
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    
    log_path = cfg["log_path"]
    setup_logging(log_path, debug=bool(cfg.get("debug_mode", False)))
    log = logging.getLogger("enhanced_agent")
    
    os.environ.setdefault("AGNO_TELEMETRY", "false")
    
    agent_type = cfg.get("agent_type", "base")
    log.info(f"=== Starting Enhanced {agent_type.title()} Agent ===")
    
    # Create model
    model = OpenAILike(
        id=cfg.get("model_name", ""),
        base_url=cfg.get("base_url", ""),
        api_key=cfg.get("api_key", ""),
    )
    
    # Create database
    db = SqliteDb(db_file=cfg.get("db_file", "agent.db"))
    
    # Create agent with tools based on type
    tools = []
    
    if agent_type == "orchestrator":
        # Orchestrator gets agent communication tools
        base_port = cfg.get("base_port", 8000)
        orchestrator_name = cfg.get("agent_name", "")
        call_agent = create_agent_caller(base_port, orchestrator_name)
        tools = [call_agent]
        log.info("Orchestrator configured with agent calling tools")
        
    elif agent_type in ["employee", "project", "timesheet", "calendar"]:
        # Subagents get Odoo data access tools
        odoo_config = cfg.get("odoo_config", {})
        search_read = create_odoo_xmlrpc_tools(
            odoo_url=odoo_config.get("url", "http://localhost:8069"),
            db=odoo_config.get("database", "burna"),
            username=odoo_config.get("username", "admin"),
            password=odoo_config.get("password", "admin"),
        )
        
        if agent_type == "employee":
            def search_employees(department: str = None) -> str:
                """
                Search for employees in Odoo.
                
                Args:
                    department: Optional department name to filter by (e.g., "Sales", "IT")
                    
                Returns:
                    List of employees with their details
                """
                return get_employees(search_read, department)
            
            tools = [search_employees]
        elif agent_type == "project":
            def list_projects() -> str:
                """List all active projects with their details."""
                return get_projects(search_read)
            
            def list_project_tasks(project_name: str = None) -> str:
                """
                List tasks, optionally filtered by project.
                
                Args:
                    project_name: Optional project name to filter tasks
                """
                return get_project_tasks(search_read, project_name)
            
            tools = [list_projects, list_project_tasks]
        elif agent_type == "timesheet":
            def get_timesheet_data(employee_name: str = None, project_name: str = None, days: int = 7) -> str:
                """
                Get timesheet entries.
                
                Args:
                    employee_name: Optional employee name to filter
                    project_name: Optional project name to filter
                    days: Number of days to look back (default: 7)
                """
                return get_timesheets(search_read, employee_name, project_name, days)
            
            tools = [get_timesheet_data]
        elif agent_type == "calendar":
            def get_upcoming_calendar_events(days: int = 7) -> str:
                """
                Get upcoming calendar events.
                
                Args:
                    days: Number of days ahead to look (default: 7)
                """
                return get_calendar_events(search_read, days)
            
            tools = [get_upcoming_calendar_events]
        
        log.info(f"{agent_type.title()} agent configured with {len(tools)} Odoo tools")
    
    # Create agent
    agent = Agent(
        id=cfg.get("agent_name", ""),
        name=cfg.get("agent_name", ""),
        role=cfg.get("agent_role", ""),
        model=model,
        instructions=cfg.get("instructions", ""),
        db=db,
        tools=tools if tools else None,
        add_history_to_context=bool(cfg.get("add_history_to_context", True)),
        add_datetime_to_context=bool(cfg.get("add_datetime_to_context", False)),
        markdown=bool(cfg.get("markdown", True)),
        debug_mode=bool(cfg.get("debug_mode", False)),
        num_history_runs=int(cfg.get("num_history_runs", 5)),
        # Note: show_tool_calls and stream removed - not supported in this agno version
    )
    
    # Start agent OS
    agent_os = AgentOS(agents=[agent])
    app = agent_os.get_app()
    
    host = cfg.get("host", "0.0.0.0")
    port = int(cfg.get("port", 7777))
    
    log.info(f"Serving {agent_type} agent on http://{host}:{port}")
    agent_os.serve(app=app, host=host, port=port, reload=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.getLogger("enhanced_agent").error(f"Agent crashed: {e}")
        logging.getLogger("enhanced_agent").error(traceback.format_exc())
        raise

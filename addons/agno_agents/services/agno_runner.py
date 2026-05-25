# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
import time
import logging
import traceback
import xmlrpc.client
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb


def mask_secret(value: str, show: int = 6):
    if not value:
        return "<EMPTY>"
    if len(value) <= show:
        return "*" * len(value)
    return value[:show] + ("*" * (len(value) - show))


def setup_logging(log_path: str, debug: bool = True):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("httpx").setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.DEBUG if debug else logging.INFO)


def create_odoo_tools(agent_type: str, odoo_config: dict, log):
    """Create tools for agents to query Odoo data"""
    if not odoo_config:
        log.warning("No odoo_config found, agent will not have data access tools")
        return []

    try:
        # Connect to Odoo via XML-RPC
        odoo_url = odoo_config.get("url", "http://localhost:8069")
        database = odoo_config.get("database", "odoo")
        username = odoo_config.get("username", "admin")
        password = odoo_config.get("password", "admin")

        log.info(f"Connecting to Odoo at {odoo_url}")
        common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
        uid = common.authenticate(database, username, password, {})

        if not uid:
            log.error("Failed to authenticate with Odoo")
            return []

        log.info(f"Authenticated with Odoo as user {uid}")
        models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')

        def search_read(model: str, domain=None, fields=None, limit: int = 80):
            """Search and read records from Odoo"""
            domain = domain or []
            fields = fields or []
            try:
                records = models.execute_kw(
                    database, uid, password,
                    model, 'search_read',
                    [domain],
                    {'fields': fields, 'limit': limit}
                )
                return records
            except Exception as e:
                log.error(f"Error querying {model}: {e}")
                return []

        # Create tools based on agent type
        tools = []

        if agent_type == "employee":
            def search_employees(name: str = None, department: str = None) -> str:
                """
                Search for employees in Odoo.

                Args:
                    name: Optional employee name to search for
                    department: Optional department name to filter by

                Returns:
                    Formatted list of employees with their details
                """
                try:
                    domain = [('active', '=', True)]

                    # Add name filter if provided
                    if name:
                        domain.append(('name', 'ilike', name))

                    # Add department filter if provided
                    if department:
                        depts = search_read(
                            'hr.department',
                            [('name', 'ilike', department)],
                            ['id', 'name'],
                            limit=1
                        )
                        if depts:
                            domain.append(('department_id', '=', depts[0]['id']))
                        else:
                            return f"Department '{department}' not found."

                    employees = search_read(
                        'hr.employee',
                        domain,
                        ['name', 'department_id', 'job_title', 'work_email', 'work_phone'],
                        limit=100
                    )

                    if not employees:
                        filters = []
                        if name:
                            filters.append(f"name like '{name}'")
                        if department:
                            filters.append(f"department '{department}'")
                        filter_str = " with " + " and ".join(filters) if filters else ""
                        return f"No employees found{filter_str}."

                    result = f"Found {len(employees)} employee(s):\n\n"
                    for emp in employees:
                        result += f"• {emp['name']}"
                        if emp.get('department_id'):
                            result += f" - {emp['department_id'][1]}"
                        if emp.get('job_title'):
                            result += f" ({emp['job_title']})"
                        result += "\n"
                        if emp.get('work_email'):
                            result += f"  Email: {emp['work_email']}\n"
                        if emp.get('work_phone'):
                            result += f"  Phone: {emp['work_phone']}\n"

                    return result
                except Exception as e:
                    return f"Error searching employees: {str(e)}"

            def get_employee_details(employee_name: str) -> str:
                """
                Get detailed information about a specific employee.

                Args:
                    employee_name: Name of the employee

                Returns:
                    Detailed employee information
                """
                try:
                    employees = search_read(
                        'hr.employee',
                        [('name', 'ilike', employee_name)],
                        ['name', 'department_id', 'job_title', 'work_email',
                         'work_phone', 'mobile_phone', 'work_location_id', 'coach_id'],
                        limit=1
                    )

                    if not employees:
                        return f"Employee '{employee_name}' not found."

                    emp = employees[0]
                    result = f"Employee Details: {emp['name']}\n\n"

                    if emp.get('job_title'):
                        result += f"Position: {emp['job_title']}\n"
                    if emp.get('department_id'):
                        result += f"Department: {emp['department_id'][1]}\n"
                    if emp.get('work_email'):
                        result += f"Email: {emp['work_email']}\n"
                    if emp.get('work_phone'):
                        result += f"Work Phone: {emp['work_phone']}\n"
                    if emp.get('mobile_phone'):
                        result += f"Mobile: {emp['mobile_phone']}\n"
                    if emp.get('work_location_id'):
                        result += f"Location: {emp['work_location_id'][1]}\n"
                    if emp.get('coach_id'):
                        result += f"Manager: {emp['coach_id'][1]}\n"

                    return result
                except Exception as e:
                    return f"Error getting employee details: {str(e)}"

            def list_departments() -> str:
                """
                List all departments in the organization.

                Returns:
                    List of all departments
                """
                try:
                    depts = search_read(
                        'hr.department',
                        [],
                        ['name', 'manager_id', 'parent_id'],
                        limit=100
                    )

                    if not depts:
                        return "No departments found."

                    result = f"Found {len(depts)} department(s):\n\n"
                    for dept in depts:
                        result += f"• {dept['name']}"
                        if dept.get('manager_id'):
                            result += f" (Manager: {dept['manager_id'][1]})"
                        result += "\n"

                    return result
                except Exception as e:
                    return f"Error listing departments: {str(e)}"

            tools = [search_employees, get_employee_details, list_departments]
            log.info(f"Created {len(tools)} employee tools")

        return tools

    except Exception as e:
        log.error(f"Failed to create Odoo tools: {e}")
        log.error(traceback.format_exc())
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to JSON config")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    log_path = cfg["log_path"]
    setup_logging(log_path, debug=bool(cfg.get("debug_mode", False)))
    log = logging.getLogger("agno_runner")

    os.environ.setdefault("AGNO_TELEMETRY", "false")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    log.info("=== Agno Agent starting ===")
    log.info("time=%s", time.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("python=%s", sys.executable)
    log.info("cwd=%s", os.getcwd())
    log.info("config_path=%s", args.config)
    log.info("log_path=%s", log_path)

    api_key = cfg.get("api_key", "")
    log.info("agent_name=%s", cfg.get("agent_name", ""))
    log.info("host=%s", cfg.get("host", "0.0.0.0"))
    log.info("port=%s", cfg.get("port", 7777))
    log.info("model_name=%s", cfg.get("model_name", ""))
    log.info("base_url=%s", cfg.get("base_url", ""))
    log.info("db_file=%s", cfg.get("db_file", "agent.db"))
    log.info("api_key_length=%s", len(api_key))
    log.info("api_key_preview=%s", mask_secret(api_key, 6))

    model = OpenAILike(
        id=cfg.get("model_name", ""),
        base_url=cfg.get("base_url", ""),
        api_key=api_key,
    )

    db = SqliteDb(db_file=cfg.get("db_file", "agent.db"))

    # Create tools based on agent type
    agent_type = cfg.get("agent_type", "")
    odoo_config = cfg.get("odoo_config", {})
    tools = []

    if agent_type and odoo_config:
        log.info(f"Creating tools for {agent_type} agent")
        tools = create_odoo_tools(agent_type, odoo_config, log)
        if tools:
            log.info(f"Successfully created {len(tools)} tools")
        else:
            log.warning("No tools were created")
    else:
        if not agent_type:
            log.info("No agent_type specified, creating agent without tools")
        if not odoo_config:
            log.info("No odoo_config specified, creating agent without tools")

    agent_obj = Agent(
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
    )
    log.info("Agent OS serving agent with ID: %s", agent_obj.id)
    
    agent_os = AgentOS(agents=[agent_obj])
    app = agent_os.get_app()

    host = cfg.get("host", "0.0.0.0")
    port = int(cfg.get("port", 7777))

    log.info("Serving on http://%s:%s", host, port)
    agent_os.serve(app=app, host=host, port=port, reload=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.getLogger("agno_runner").error("Agent crashed: %s", e)
        logging.getLogger("agno_runner").error(traceback.format_exc())
        raise

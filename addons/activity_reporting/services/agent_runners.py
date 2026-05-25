# -*- coding: utf-8 -*-
"""
Custom Agent Runners for Activity Reporting

This module provides specialized agent runners that integrate Odoo tools
with Agno agents. Each runner is configured for a specific domain
(employees, todos, projects, timesheets, calendars).
"""

import argparse
import json
import os
import sys
import logging
import traceback
import requests
from typing import Dict, Any

from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb

# Import Odoo tools
from .odoo_tools import (
    OdooEmployeeTool,
    OdooTodoTool,
    OdooProjectTool,
    OdooTimesheetTool,
    OdooCalendarTool,
)


def setup_logging(log_path: str, debug: bool = True):
    """Configure logging for agent runners"""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)


def create_base_agent(cfg: Dict[str, Any]) -> Agent:
    """Create a base Agno agent with common configuration"""
    
    api_key = cfg.get("api_key", "")
    
    model = OpenAILike(
        id=cfg.get("model_name", ""),
        base_url=cfg.get("base_url", ""),
        api_key=api_key,
    )
    
    db = SqliteDb(db_file=cfg.get("db_file", "agent.db"))
    
    agent = Agent(
        id=cfg.get("agent_name", ""),
        name=cfg.get("agent_name", ""),
        role=cfg.get("agent_role", ""),
        model=model,
        instructions=cfg.get("instructions", ""),
        db=db,
        add_history_to_context=bool(cfg.get("add_history_to_context", True)),
        add_datetime_to_context=bool(cfg.get("add_datetime_to_context", False)),
        markdown=bool(cfg.get("markdown", True)),
        debug_mode=bool(cfg.get("debug_mode", False)),
        num_history_runs=int(cfg.get("num_history_runs", 5)),
    )
    
    return agent


def run_employee_agent():
    """Run the employee agent with Odoo integration"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to JSON config")
    args = parser.parse_args()
    
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    
    log_path = cfg["log_path"]
    setup_logging(log_path, debug=bool(cfg.get("debug_mode", False)))
    log = logging.getLogger("employee_agent")
    
    os.environ.setdefault("AGNO_TELEMETRY", "false")
    
    log.info("=== Employee Agent Starting ===")
    
    # Get Odoo connection details from config or use defaults
    odoo_url = cfg.get("odoo_url", "http://127.0.0.1:8069")
    odoo_db = cfg.get("odoo_database", "odoo")
    odoo_user = cfg.get("odoo_username", "admin")
    odoo_pass = cfg.get("odoo_password", "admin")
    
    log.info("Connecting to Odoo at %s, database: %s, user: %s", odoo_url, odoo_db, odoo_user)
    
    # Create Odoo employee tool
    try:
        employee_tool = OdooEmployeeTool(
            odoo_url=odoo_url,
            database=odoo_db,
            username=odoo_user,
            password=odoo_pass,
        )
        log.info("OdooEmployeeTool initialized successfully")
    except Exception as e:
        log.error("Failed to initialize OdooEmployeeTool: %s", e)
        # Continue anyway - agent will start but tools won't work
        employee_tool = None
    
    # Create base agent
    agent = create_base_agent(cfg)
    
    # Register the Odoo tools with the agent
    if employee_tool:
        agent.register_tool(employee_tool.search_employees)
        agent.register_tool(employee_tool.get_employee_details)
        log.info("Registered 2 Odoo tools with employee agent")
    else:
        log.warning("Employee tools not registered - Odoo connection failed")
    
    # Start agent OS
    agent_os = AgentOS(agents=[agent])
    app = agent_os.get_app()
    
    host = cfg.get("host", "0.0.0.0")
    port = int(cfg.get("port", 7777))
    
    log.info("Serving Employee Agent on http://%s:%s", host, port)
    agent_os.serve(app=app, host=host, port=port, reload=False)


def run_orchestrator_agent():
    """Run the orchestrator agent with subagent communication tools"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to JSON config")
    args = parser.parse_args()
    
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    
    log_path = cfg["log_path"]
    setup_logging(log_path, debug=bool(cfg.get("debug_mode", False)))
    log = logging.getLogger("orchestrator_agent")
    
    os.environ.setdefault("AGNO_TELEMETRY", "false")
    
    log.info("=== Orchestrator Agent Starting ===")
    
    # Create base agent
    agent = create_base_agent(cfg)
    
    # Get base port for calculating subagent ports
    base_port = int(cfg.get("port", 8000))
    
    # Define subagent endpoints
    subagent_ports = {
        "employee": base_port + 1,
        "todo": base_port + 2,
        "project": base_port + 3,
        "timesheet": base_port + 4,
        "calendar": base_port + 5,
    }
    
    log.info("Subagent ports: %s", subagent_ports)
    
    # Create tool functions for communicating with subagents
    def ask_employee_agent(query: str) -> str:
        """
        Ask the Employee Agent about employee information.
        
        Args:
            query: Question about employees (e.g., "who are all employees?", "find employee John")
            
        Returns:
            Response from the Employee Agent with employee information
        """
        port = subagent_ports["employee"]
        # Extract reporter ID from orchestrator name (e.g., "activity_orchestrator_1" -> "1")
        orchestrator_name = cfg.get("agent_name", "")
        reporter_id = orchestrator_name.split("_")[-1] if "_" in orchestrator_name else "1"
        agent_name = f"employee_agent_{reporter_id}"
        
        url = f"http://127.0.0.1:{port}/agents/{agent_name}/runs"
        
        payload = {
            "message": query,
            "session_id": "orchestrator_to_employee",
            "stream": True,
        }
        
        try:
            log.info("Calling Employee Agent at port %s with query: %s", port, query[:100])
            
            response = requests.post(
                url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
                stream=True,
            )
            response.raise_for_status()
            
            full_content = ""
            for line in response.iter_lines():
                if not line:
                    continue
                
                decoded_line = line.decode("utf-8", errors="ignore").strip()
                
                if not decoded_line.startswith("data:"):
                    continue
                
                data_str = decoded_line[5:].strip()
                
                try:
                    event_data = json.loads(data_str)
                    ev = event_data.get("event")
                    
                    if ev == "RunContent":
                        full_content += event_data.get("content", "") or ""
                    elif ev == "RunCompleted":
                        final = (event_data.get("content") or "").strip()
                        full_content = final or full_content.strip()
                        break
                
                except json.JSONDecodeError:
                    full_content += data_str + "\n"
            
            result = (full_content or "").strip()
            log.info("Received response from Employee Agent: %s", result[:200])
            return result
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Error communicating with Employee Agent: {str(e)}"
            log.error(error_msg)
            return error_msg
    
    # Register the subagent communication tool
    agent.register_tool(ask_employee_agent)
    log.info("Registered ask_employee_agent tool with orchestrator")
    
    # Start agent OS
    agent_os = AgentOS(agents=[agent])
    app = agent_os.get_app()
    
    host = cfg.get("host", "0.0.0.0")
    port = base_port
    
    log.info("Serving Orchestrator Agent on http://%s:%s", host, port)
    agent_os.serve(app=app, host=host, port=port, reload=False)


# Entry points for different agent types
if __name__ == "__main__":
    agent_type = os.environ.get("AGENT_TYPE", "base")
    
    try:
        if agent_type == "employee":
            run_employee_agent()
        elif agent_type == "orchestrator":
            run_orchestrator_agent()
        else:
            # Default to base agent runner (same as agno_runner.py)
            parser = argparse.ArgumentParser()
            parser.add_argument("--config", required=True, help="Path to JSON config")
            args = parser.parse_args()
            
            with open(args.config, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            
            log_path = cfg["log_path"]
            setup_logging(log_path, debug=bool(cfg.get("debug_mode", False)))
            log = logging.getLogger("activity_agent")
            
            os.environ.setdefault("AGNO_TELEMETRY", "false")
            
            log.info("=== Activity Agent Starting ===")
            
            agent = create_base_agent(cfg)
            agent_os = AgentOS(agents=[agent])
            app = agent_os.get_app()
            
            host = cfg.get("host", "0.0.0.0")
            port = int(cfg.get("port", 7777))
            
            log.info("Serving on http://%s:%s", host, port)
            agent_os.serve(app=app, host=host, port=port, reload=False)
            
    except Exception as e:
        logging.getLogger("activity_agent").error("Agent crashed: %s", e)
        logging.getLogger("activity_agent").error(traceback.format_exc())
        raise

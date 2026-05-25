# -*- coding: utf-8 -*-
"""
Custom Agent Starter for Activity Reporting

This module extends the AgnoAgentService to use custom agent runners
that include Odoo tools and inter-agent communication.
"""

import os
import json
import subprocess
import logging

_logger = logging.getLogger(__name__)


class ActivityReportingAgentService:
    """Service for starting activity reporting agents with custom runners"""
    
    @staticmethod
    def get_custom_runner_path(agent_type: str):
        """Get the path to the custom runner for an agent type"""
        service_dir = os.path.dirname(__file__)
        
        if agent_type == "orchestrator":
            return os.path.join(service_dir, "agent_runners.py")
        elif agent_type == "employee":
            return os.path.join(service_dir, "agent_runners.py")
        else:
            # Use default agno runner for other agents
            return None
    
    @staticmethod
    def write_agent_config(agent, agent_type: str = None):
        """
        Write configuration file for agent with Odoo connection details
        
        Args:
            agent: The agno.agent record
            agent_type: Type of agent (orchestrator, employee, etc.)
        
        Returns:
            Path to config file
        """
        config_path = f"/tmp/agno_agent_{agent.id}.json"
        log_path = f"/tmp/agno_agent_{agent.id}.log"
        
        # Determine agent type from name if not provided
        if not agent_type:
            if "orchestrator" in agent.agent_name.lower():
                agent_type = "orchestrator"
            elif "employee" in agent.agent_name.lower():
                agent_type = "employee"
            elif "todo" in agent.agent_name.lower():
                agent_type = "todo"
            elif "project" in agent.agent_name.lower():
                agent_type = "project"
            elif "timesheet" in agent.agent_name.lower():
                agent_type = "timesheet"
            elif "calendar" in agent.agent_name.lower():
                agent_type = "calendar"
            else:
                agent_type = "base"
        
        cfg = {
            "log_path": log_path,
            "agent_name": agent.agent_name or "",
            "agent_role": agent.agent_role or "",
            "instructions": agent.instructions or "",
            "model_name": agent.model_name or "",
            "base_url": agent.base_url or "",
            "api_key": agent.api_key or "",
            "db_file": agent.db_file or "agent.db",
            "host": agent.host or "0.0.0.0",
            "port": int(agent.port),
            "add_history_to_context": bool(agent.add_history_to_context),
            "add_datetime_to_context": bool(agent.add_datetime_to_context),
            "markdown": bool(agent.markdown),
            "debug_mode": bool(agent.debug_mode),
            "num_history_runs": int(agent.num_history_runs or 5),
            
            # Add Odoo connection details for agents that need them
            "odoo_url": "http://127.0.0.1:8069",
            "odoo_database": "burna",  
            "odoo_username": "admin",
            "odoo_password": "admin",
        }
        
        # Create empty log file
        try:
            with open(log_path, "w", encoding="utf-8") as lf:
                lf.write("")
        except Exception:
            pass
        
        # Write config
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        
        try:
            os.chmod(config_path, 0o600)
        except Exception:
            pass
        
        return config_path, agent_type
    
    @classmethod
    def start_activity_agent(cls, agent, venv_py: str = "/usr/bin/python3"):
        """
        Start an activity reporting agent with appropriate custom runner
        
        Args:
            agent: The agno.agent record
            venv_py: Path to Python interpreter
            
        Returns:
            Process PID
        """
        # Write config and determine agent type
        config_path, agent_type = cls.write_agent_config(agent)
        log_path = f"/tmp/agno_agent_{agent.id}.log"
        
        # Get custom runner path
        runner_path = cls.get_custom_runner_path(agent_type)
        
        if not runner_path or not os.path.exists(runner_path):
            # Fall back to standard agno_agents service
            _logger.warning("No custom runner found for %s, using standard service", agent_type)
            from odoo.addons.agno_agents.services.agno_services import AgnoAgentService
            return AgnoAgentService.start_agent_process(agent, venv_py)
        
        _logger.info("Starting %s agent using custom runner: %s", agent_type, runner_path)
        
        # Open log file
        logf = open(log_path, "a", encoding="utf-8")
        
        # Set environment variable for agent type
        env = os.environ.copy()
        env["AGENT_TYPE"] = agent_type
        env["AGNO_TELEMETRY"] = "false"
        env["PYTHONUNBUFFERED"] = "1"
        
        # Start process
        process = subprocess.Popen(
            [venv_py, "-u", runner_path, "--config", config_path],
            stdout=logf,
            stderr=logf,
            env=env,
            preexec_fn=os.setsid,
            close_fds=True,
        )
        
        _logger.info("Started %s agent (PID: %d) on port %d", agent_type, process.pid, agent.port)
        
        return process.pid

# -*- coding: utf-8 -*-
"""
Activity Reporting Agent Service

This extends the standard Agno agent service to use the enhanced runner
with proper tool integration for Odoo data access.
"""

import os
import json
import logging
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ActivityAgentService:
    """Service for managing activity reporting agents"""
    
    @staticmethod
    def enhanced_runner_path():
        """Path to the enhanced runner script"""
        return os.path.join(os.path.dirname(__file__), "enhanced_runner.py")
    
    @staticmethod
    def write_enhanced_config(agent, agent_type: str, base_port: int = None) -> str:
        """
        Write configuration for enhanced agent runner
        
        Args:
            agent: The agno.agent record
            agent_type: Type of agent (orchestrator, employee, project, etc.)
            base_port: Base port for orchestrator (only needed for orchestrator)
        """
        from odoo.addons.agno_agents.services.agno_services import AgnoAgentService
        
        cfg_path = AgnoAgentService.config_path(agent.id)
        log_path = AgnoAgentService.log_path(agent.id)
        
        # Base configuration
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
            "agent_type": agent_type,
        }
        
        # Add base_port for orchestrator
        if agent_type == "orchestrator" and base_port:
            cfg["base_port"] = base_port
        
        # Add Odoo configuration for subagents
        if agent_type in ["employee", "project", "timesheet", "calendar", "todo"]:
            ICP = agent.env["ir.config_parameter"].sudo()
            cfg["odoo_config"] = {
                "url": ICP.get_param("activity_reporting.odoo_url", "http://localhost:8069"),
                "database": agent.env.cr.dbname,
                "username": ICP.get_param("activity_reporting.odoo_username", "admin"),
                "password": ICP.get_param("activity_reporting.odoo_password", "admin"),
            }
        
        # Clear log file
        try:
            with open(log_path, "w", encoding="utf-8") as lf:
                lf.write("")
        except Exception:
            pass
        
        # Write config
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        
        try:
            os.chmod(cfg_path, 0o600)
        except Exception:
            pass
        
        return cfg_path
    
    @classmethod
    def start_enhanced_agent(cls, agent, agent_type: str, base_port: int = None, venv_py: str = None):
        """
        Start an agent using the enhanced runner
        
        Args:
            agent: The agno.agent record
            agent_type: Type of agent (orchestrator, employee, project, etc.)
            base_port: Base port for orchestrator
            venv_py: Path to Python interpreter
        """
        import subprocess
        import time
        import signal
        from odoo.addons.agno_agents.services.agno_services import AgnoAgentService
        
        # Check if agno library is installed
        check_cmd = [venv_py or AgnoAgentService.DEFAULT_VENV_PY, "-c", "import agno"]
        try:
            subprocess.run(check_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            error_msg = """The 'agno' library is not installed.

To fix this, run in your Odoo container:
  pip install agno --break-system-packages
  
Or if using a virtual environment:
  source /path/to/venv/bin/activate
  pip install agno

For more details, see the requirements.txt file in the activity_reporting module."""
            _logger.error(error_msg)
            raise UserError(_(error_msg))
        
        venv_py = venv_py or AgnoAgentService.DEFAULT_VENV_PY
        
        runner = cls.enhanced_runner_path()
        if not os.path.exists(runner):
            raise UserError(_(f"Enhanced runner not found: {runner}"))
        
        # Check if port is available
        if AgnoAgentService.ss_available() and AgnoAgentService.port_is_listening(agent.port):
            raise UserError(
                _(f"Port {agent.port} is already in use. Stop the process or change the port.")
            )
        
        # Write configuration
        cfg_path = cls.write_enhanced_config(agent, agent_type, base_port)
        log_path = AgnoAgentService.log_path(agent.id)
        
        # Start process
        logf = open(log_path, "a", encoding="utf-8")
        
        process = subprocess.Popen(
            [venv_py, "-u", runner, "--config", cfg_path],
            stdout=logf,
            stderr=logf,
            preexec_fn=os.setsid,
            close_fds=True,
        )
        
        # Wait for process to start
        time.sleep(2)
        if process.poll() is not None:
            # Process exited immediately - get the error details
            r = subprocess.run(
                [venv_py, "-u", runner, "--config", cfg_path],
                capture_output=True,
                text=True,
                check=False,
            )
            
            # Read log file for additional context
            log_content = ""
            try:
                with open(log_path, "r", encoding="utf-8") as lf:
                    log_content = lf.read()[-2000:]  # Last 2000 chars
            except Exception:
                pass
            
            error_msg = (r.stderr or r.stdout or "").strip()
            if not error_msg and log_content:
                error_msg = log_content
            if not error_msg:
                error_msg = "Agent process exited immediately with no error output."
            
            # Include the log file path in the error
            full_error = f"Failed to start {agent_type} agent.\n\nError: {error_msg}\n\nCheck log file: {log_path}"
            _logger.error(full_error)
            raise UserError(_(full_error))
        
        # Wait for port to be listening
        if AgnoAgentService.ss_available():
            for i in range(10):
                if AgnoAgentService.port_is_listening(agent.port):
                    break
                time.sleep(0.3)
        
        _logger.info(f"Started {agent_type} agent with PID {process.pid} on port {agent.port}")
        return process.pid

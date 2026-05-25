# -*- coding: utf-8 -*-
"""
Agno Tools for Activity Reporting

These tools enable the orchestrator agent to communicate with specialized subagents
and query Odoo data directly.
"""

import logging
import requests
import json
from typing import List, Dict, Any, Optional

_logger = logging.getLogger(__name__)


class SubAgentTool:
    """Base class for communicating with subagents"""
    
    def __init__(self, agent_name: str, host: str = "127.0.0.1", port: int = 8001):
        self.agent_name = agent_name
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
    
    def query(self, message: str, session_id: str = "orchestrator") -> str:
        """Send a query to the subagent and get response"""
        url = f"{self.base_url}/agents/{self.agent_name}/runs"
        
        payload = {
            "message": message,
            "session_id": session_id,
            "stream": True,
        }
        
        try:
            response = requests.post(
                url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=60,
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
            
            return (full_content or "").strip()
        
        except requests.exceptions.RequestException as e:
            _logger.error("Failed to query subagent %s: %s", self.agent_name, e)
            return f"Error communicating with {self.agent_name}: {str(e)}"


class OdooDataTool:
    """Tool for querying Odoo data directly"""
    
    def __init__(self, odoo_env):
        """
        Initialize with Odoo environment
        
        Args:
            odoo_env: Odoo environment object with database access
        """
        self.env = odoo_env
    
    def get_projects(self, active_only: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of projects"""
        domain = [('active', '=', True)] if active_only else []
        
        try:
            projects = self.env['project.project'].search(domain, limit=limit)
            result = []
            
            for project in projects:
                # Count tasks
                task_count = self.env['project.task'].search_count([
                    ('project_id', '=', project.id)
                ])
                
                completed_tasks = self.env['project.task'].search_count([
                    ('project_id', '=', project.id),
                    ('stage_id.is_closed', '=', True)
                ])
                
                result.append({
                    'id': project.id,
                    'name': project.name,
                    'active': project.active,
                    'task_count': task_count,
                    'completed_tasks': completed_tasks,
                    'progress': (completed_tasks / task_count * 100) if task_count > 0 else 0,
                })
            
            return result
        
        except Exception as e:
            _logger.error("Failed to get projects: %s", e)
            return []
    
    def get_employees(self, active_only: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of employees"""
        domain = [('active', '=', True)] if active_only else []
        
        try:
            employees = self.env['hr.employee'].search(domain, limit=limit)
            result = []
            
            for emp in employees:
                result.append({
                    'id': emp.id,
                    'name': emp.name,
                    'job_title': emp.job_title or '',
                    'department': emp.department_id.name if emp.department_id else '',
                    'work_email': emp.work_email or '',
                })
            
            return result
        
        except Exception as e:
            _logger.error("Failed to get employees: %s", e)
            return []
    
    def get_tasks(self, project_id: Optional[int] = None, 
                  user_id: Optional[int] = None, 
                  limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of tasks"""
        domain = []
        
        if project_id:
            domain.append(('project_id', '=', project_id))
        
        if user_id:
            domain.append(('user_ids', 'in', [user_id]))
        
        try:
            tasks = self.env['project.task'].search(domain, limit=limit)
            result = []
            
            for task in tasks:
                result.append({
                    'id': task.id,
                    'name': task.name,
                    'project': task.project_id.name if task.project_id else '',
                    'assigned_to': [u.name for u in task.user_ids],
                    'stage': task.stage_id.name if task.stage_id else '',
                    'priority': task.priority,
                    'deadline': task.date_deadline.isoformat() if task.date_deadline else None,
                })
            
            return result
        
        except Exception as e:
            _logger.error("Failed to get tasks: %s", e)
            return []
    
    def get_timesheets(self, employee_id: Optional[int] = None,
                       project_id: Optional[int] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """Get timesheet entries"""
        domain = []
        
        if employee_id:
            domain.append(('employee_id', '=', employee_id))
        
        if project_id:
            domain.append(('project_id', '=', project_id))
        
        if date_from:
            domain.append(('date', '>=', date_from))
        
        if date_to:
            domain.append(('date', '<=', date_to))
        
        try:
            timesheets = self.env['account.analytic.line'].search(domain, limit=limit)
            result = []
            
            for ts in timesheets:
                result.append({
                    'id': ts.id,
                    'date': ts.date.isoformat() if ts.date else None,
                    'employee': ts.employee_id.name if ts.employee_id else '',
                    'project': ts.project_id.name if ts.project_id else '',
                    'task': ts.task_id.name if ts.task_id else '',
                    'hours': float(ts.unit_amount),
                    'description': ts.name or '',
                })
            
            return result
        
        except Exception as e:
            _logger.error("Failed to get timesheets: %s", e)
            return []
    
    def get_calendar_events(self, user_id: Optional[int] = None,
                           date_from: Optional[str] = None,
                           date_to: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Get calendar events"""
        domain = []
        
        if user_id:
            domain.append(('partner_ids', 'in', [self.env['res.users'].browse(user_id).partner_id.id]))
        
        if date_from:
            domain.append(('start', '>=', date_from))
        
        if date_to:
            domain.append(('stop', '<=', date_to))
        
        try:
            events = self.env['calendar.event'].search(domain, limit=limit)
            result = []
            
            for event in events:
                result.append({
                    'id': event.id,
                    'name': event.name,
                    'start': event.start.isoformat() if event.start else None,
                    'stop': event.stop.isoformat() if event.stop else None,
                    'location': event.location or '',
                    'attendees': [p.name for p in event.partner_ids],
                })
            
            return result
        
        except Exception as e:
            _logger.error("Failed to get calendar events: %s", e)
            return []

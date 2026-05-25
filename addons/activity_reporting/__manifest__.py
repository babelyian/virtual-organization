# -*- coding: utf-8 -*-
{
    'name': 'Current Activity Reporting',
    'version': '1.0',
    'category': 'Productivity',
    'summary': 'Multi-agent system for reporting current activities across modules',
    'description': """
        Current Activity Reporting Module
        ==================================
        
        This module provides an intelligent multi-agent system for reporting
        current activities across different Odoo modules:
        
        * Orchestrator Agent: Coordinates requests and delegates to subagents
        * Employee Agent: Retrieves employee information and activities
        * Todo Agent: Manages and reports on todo tasks
        * Project Agent: Reports on project status and tasks
        * Timesheet Agent: Analyzes timesheet entries and time tracking
        * Calendar Agent: Provides calendar events and meeting information
        
        The orchestrator agent can be linked to an Odoo bot user for
        conversational interaction through Odoo discussions.
    """,
    'author': 'Mahan',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'mail',
        'hr',
        'project',
        'hr_timesheet',
        'calendar',
        'agno_agents',
        'agno_user',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/activity_reporting_views.xml',
        'data/activity_reporting_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

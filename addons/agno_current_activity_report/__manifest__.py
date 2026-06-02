{
    'name': 'Agno Current Activity Report',
    'version': '1.0.0',
    'summary': 'Agno Agent reporting module for Odoo',
    'description': '''
        This module allows users to define and activate Agno agents for obtaining current activity reporting within Odoo.
        Features:
        - Create and configure Agno agents
        - Simple agent property management
        - Agent activation/deactivation
        - Serves agents on specified port
    ''',
    'author': 'Burna',
    'website': 'https://www.burna.com',
    'category': 'Tools',
    'depends': ['base', 'mail', 'agno_agents'],
    'version_info': (19, 0, 1),
    'data': [
        'security/ir.model.access.csv',
        'data/agno_server_actions.xml',
        'data/ir_cron.xml',
        'views/agno_current_activity_report_views.xml',
        'views/agno_current_activity_report_views_menus.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
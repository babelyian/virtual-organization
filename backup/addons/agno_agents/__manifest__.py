{
    'name': 'Agno Agents',
    'version': '1.0.0',
    'summary': 'Agno Agent management module for Odoo',
    'description': '''
        This module allows users to define and activate Agno agents within Odoo.
        Features:
        - Create and configure Agno agents
        - Simple agent property management
        - Agent activation/deactivation
        - Serves agents on specified port
    ''',
    'author': 'Your Company',
    'website': 'https://www.burna.com',
    'category': 'Tools',
    'depends': ['base', 'mail'],
    'version_info': (19, 0, 1),
    'data': [
        'security/ir.model.access.csv',
        'data/agno_server_actions.xml',
        'data/ir_cron.xml',
        'views/agno_agent_views.xml',
        'views/agno_menus.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
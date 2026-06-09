{
    'name': "Agno Agent Users",
    'summary': "Agno Agents as bot users in Odoo Discuss channels",
    'description': """
    Allows admins to create special bot users in the UI linked to external Agno Agents.
    When a bot user is added to a channel, it automatically answers prompts via the agent's API.
    """,
    'author': "Mansour",
    'category': 'Tools',
    'version': '1.0.0',
    'depends': ['mail', 'agno_agents'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_users_views.xml',   
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
            'web.assets_backend': [
                'agno_user/static/src/scss/discuss_fix.scss',
                'agno_user/static/src/js/discuss_override.js',
            ],
        },
}
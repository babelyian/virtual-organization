{
    'name': "Agno Agents - Discuss Integration",
    'summary': "Talk to Agno Agents directly in Odoo Discuss channels",
    'description': """
    Allows users to create Discuss channels connected to external Agno Agents.
    Messages are sent to the agent's API and responses appear as bot messages.
    Supports both streaming and non-streaming agents.
    """,
    'author': "Your Name",
    'category': 'Tools',
    'version': '1.0.0',                     # ←←← Change here
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/agno_bot_data.xml',
        'views/agno_agent_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',                    # ← Bonus: add this to silence the license warning
}
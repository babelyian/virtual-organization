{
    'name': 'Library Management',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Manage library books',
    'description': """
        Custom module to manage library books.
        Includes models, views, menus, security, and a JSON API controller.
    """,
    'author': 'mansour davoudi',
    'website': 'https://burna.com',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/library_book_views.xml',
        'views/library_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
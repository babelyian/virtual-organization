from odoo import models, fields

class Book(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _order = 'name'

    name = fields.Char(string='Title', required=True)
    author = fields.Char(string='Author')
    publish_date = fields.Date(string='Publish Date')
    isbn = fields.Char(string='ISBN')
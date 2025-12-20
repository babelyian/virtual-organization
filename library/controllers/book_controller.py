from odoo import http
from odoo.http import request

class BookController(http.Controller):

    @http.route('/api/library/books', type='json', auth='user', methods=['GET'], csrf=False)
    def list_books(self, **kwargs):
        """Return a list of books (authenticated users only)."""
        books = request.env['library.book'].search([])
        return [
            {
                'id': book.id,
                'title': book.name,
                'author': book.author,
                'publish_date': book.publish_date,
                'isbn': book.isbn,
            } for book in books
        ]

    @http.route('/api/library/books/<int:book_id>', type='json', auth='public', methods=['GET'], csrf=False)
    def get_book(self, book_id, **kwargs):
        """Return a single book (public access)."""
        book = request.env['library.book'].browse(book_id)
        if not book.exists():
            return {'error': 'Book not found'}
        return {
            'id': book.id,
            'title': book.name,
            'author': book.author,
        }
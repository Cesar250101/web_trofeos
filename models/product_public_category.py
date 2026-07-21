from odoo import fields, models


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    woo_category_id = fields.Char(
        string='WooCommerce Category ID',
        index=True,
        copy=False,
        help='ID de la categoría en WooCommerce. Se usa para mapear de forma '
             'estable las categorías del ecommerce con las de la tienda WooCommerce '
             'y asignar public_categ_ids a los productos.',
    )

    def tr_get_showcase_product(self):
        """Return the first published product with a real image for this category."""
        self.ensure_one()
        Template = self.env['product.template'].sudo()
        cat_ids = self.search([('id', 'child_of', self.id)]).ids or [self.id]
        return Template.search([
            ('public_categ_ids', 'in', cat_ids),
            ('is_published', '=', True),
            ('image_1920', '!=', False),
        ], order='is_published desc, id asc', limit=1)

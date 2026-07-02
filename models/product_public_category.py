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

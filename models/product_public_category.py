from odoo import models


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    def tr_get_showcase_product(self):
        """Return the first published product with a real image for this category.

        Used by the "Explora por Categorías" snippet to display a real product
        photo instead of the generated placeholder SVG. Searches the category
        itself first, then any descendant categories (many root categories such
        as Trofeos, Medallas or Deportes only hold products in their children).

        Returns a ``product.template`` recordset (empty if none found).
        """
        self.ensure_one()
        Template = self.env['product.template'].sudo()
        # All descendant categories (including self), resolved via parent_path.
        cat_ids = self.search([('id', 'child_of', self.id)]).ids or [self.id]
        return Template.search([
            ('public_categ_ids', 'in', cat_ids),
            ('is_published', '=', True),
            ('image_1920', '!=', False),
        ], order='is_published desc, id asc', limit=1)

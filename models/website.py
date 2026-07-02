from odoo import api, models
from odoo.addons.web_trofeos import hooks as _hooks


class Website(models.Model):
    _inherit = 'website'

    @property
    def is_homepage(self):
        """True when the current request path matches this website's homepage URL.

        Newer Odoo 16 builds reference website.is_homepage in website.layout;
        this property keeps older VPS installations from crashing with
        AttributeError when that template is rendered.
        """
        try:
            from odoo.http import request as http_request
            if http_request and http_request.httprequest:
                homepage = getattr(self, 'homepage_url', None) or '/'
                return http_request.httprequest.path == homepage
        except Exception:
            pass
        return False

    @api.model
    def action_sync_wp_categories(self):
        """Sync product categories from WordPress for the Trofeos website.

        Called automatically from data/sync_categories.xml (noupdate="0")
        on every ``--update=web_trofeos``, and can also be triggered manually.
        """
        trofeos = self.search([('name', '=', 'Trofeos')], limit=1)
        if not trofeos:
            return
        _hooks._sync_categories(self.env, trofeos)
        _hooks._sync_menus(self.env, trofeos)

    @api.model
    def action_sync_woo_categories(self):
        """Sincroniza public_categ_ids de los productos desde WooCommerce (REST).

        Descarga las categorías y productos de la tienda WooCommerce, mapea cada
        categoría a su ``product.public.category`` y asigna ``public_categ_ids`` a
        los productos de Odoo emparejando por SKU (default_code).

        Se ejecuta automáticamente en cada ``--update=web_trofeos`` (post_update_hook)
        y puede lanzarse manualmente desde el shell o una acción de servidor.
        """
        trofeos = self.search([('name', '=', 'Trofeos')], limit=1)
        if not trofeos:
            return
        _hooks._sync_woo_public_categs(self.env, trofeos)

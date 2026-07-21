from odoo import api, models
from odoo.addons.web_trofeos import hooks as _hooks

# ir.config_parameter key holding the id of the "public +60%" pricelist.
TR_PUBLIC_PRICELIST_PARAM = 'web_trofeos.public_pricelist_id'


class Website(models.Model):
    _inherit = 'website'

    def _is_tr_website(self):
        self.ensure_one()
        return self.name == 'Trofeos'

    def get_current_pricelist(self):
        """Force the +60% surcharge pricelist for anonymous visitors on Trofeos.

        Logged-in users keep their normal pricelist (base sale prices). This
        override only kicks in for the public user on the Trofeos website, so
        the surcharge is applied consistently across shop, product page and
        cart without touching product base prices.
        """
        from odoo.http import request
        chose_pl = bool(request and request.session.get('website_sale_current_pl'))
        if (
            self._is_tr_website()
            and self.env.user._is_public()
            # A pricelist explicitly chosen (coupon / selector) is respected.
            and not chose_pl
        ):
            pl = self._tr_get_public_pricelist()
            if pl:
                return pl
        return super().get_current_pricelist()

    def _tr_get_public_pricelist(self):
        param = self.env['ir.config_parameter'].sudo().get_param(TR_PUBLIC_PRICELIST_PARAM)
        if not param:
            return self.env['product.pricelist']
        pl = self.env['product.pricelist'].sudo().browse(int(param)).exists()
        return pl

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
    def action_setup_public_pricelist(self):
        """Ensure the anonymous +60% pricelist exists.

        Called from data/setup_pricelist.xml on every ``--update`` so the
        surcharge survives reinstalls without relying on WooCommerce sync.
        """
        trofeos = self.search([('name', '=', 'Trofeos')], limit=1)
        if not trofeos:
            return
        _hooks._ensure_public_pricelist(self.env, trofeos)

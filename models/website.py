from odoo import api, models
from odoo.addons.web_trofeos import hooks as _hooks


class Website(models.Model):
    _inherit = 'website'

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

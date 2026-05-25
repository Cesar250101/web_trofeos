from odoo import models
from odoo.http import request

_TROFEOS_PREFIXES = (
    '/trofeos',
    '/quienes-somos-trofeos',
    '/servicios-trofeos',
    '/empresas-trofeos',
    '/contacto-trofeos',
    '/coleccion-trofeos/',
)

_trofeos_website_id = None  # module-level cache, populated on first call


def _get_trofeos_website_id(env):
    global _trofeos_website_id
    if not _trofeos_website_id:
        w = env['website'].sudo().search([('name', '=', 'Trofeos')], limit=1)
        _trofeos_website_id = w.id if w else False
    return _trofeos_website_id


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _match(cls, path):
        """
        Before the website is resolved via domain matching, check if the
        current path belongs to the Trofeos website. If so, force that website
        in the session so that get_current_website() returns it immediately.

        Root cause: website "Trofeos" (id=16) and "Method" (id=6) both have
        no domain configured and sequence=10. Odoo falls back to the one with
        the lowest id (Method), so anonymous visitors to /trofeos get Method's
        CSS bundle instead of Trofeos's.
        """
        if request and not hasattr(request, 'website_routing'):
            for prefix in _TROFEOS_PREFIXES:
                if path == prefix or path.startswith(prefix):
                    trofeos_id = _get_trofeos_website_id(request.env)
                    if trofeos_id and request.session.get('force_website_id') != trofeos_id:
                        request.session['force_website_id'] = trofeos_id
                    break
        return super()._match(path)

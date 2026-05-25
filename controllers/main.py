from odoo import http
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug

_TROFEOS_WEBSITE_NAME = 'Trofeos'


def _ensure_trofeos_website():
    """
    Force the Trofeos website in the current session so that the correct
    CSS bundle (web.assets_frontend compiled for website id=16) is served
    to unauthenticated users.

    Without this, Odoo resolves the website by HTTP host domain. Since the
    Trofeos website has no domain configured and shares sequence=10 with the
    Method website (id=6), Odoo always falls back to Method (lower id), which
    serves Method's CSS bundle -- leaving Trofeos pages unstyled for guests.
    """
    website = request.env['website'].sudo().search(
        [('name', '=', _TROFEOS_WEBSITE_NAME)], limit=1
    )
    if website and request.session.get('force_website_id') != website.id:
        request.session['force_website_id'] = website.id


class TrofeosSite(http.Controller):

    @http.route(['/trofeos'], type='http', auth='public', website=True, sitemap=True)
    def home(self, **kw):
        _ensure_trofeos_website()
        return request.render('web_trofeos.tr_home')

    @http.route(['/quienes-somos-trofeos'], type='http', auth='public', website=True, sitemap=True)
    def quienes_somos(self, **kw):
        _ensure_trofeos_website()
        return request.render('web_trofeos.tr_quienes_somos_page')

    @http.route(['/servicios-trofeos'], type='http', auth='public', website=True, sitemap=True)
    def servicios(self, **kw):
        _ensure_trofeos_website()
        return request.render('web_trofeos.tr_servicios_page')

    @http.route(['/empresas-trofeos'], type='http', auth='public', website=True, sitemap=True)
    def empresas(self, **kw):
        _ensure_trofeos_website()
        return request.render('web_trofeos.tr_empresas_page')

    @http.route(['/contacto-trofeos'], type='http', auth='public', website=True, sitemap=True)
    def contacto(self, **kw):
        _ensure_trofeos_website()
        company = request.env.company.sudo()
        return request.render('web_trofeos.tr_contacto_page', {
            'company': company,
            'tipo_producto': kw.get('tipo', ''),
            'cantidad': kw.get('cantidad', ''),
        })

    @http.route(
        ['/coleccion-trofeos/<model("product.public.category"):category>'],
        type='http', auth='public', website=True, sitemap=True,
    )
    def category_page(self, category, **kw):
        _ensure_trofeos_website()
        website = request.website
        if category.website_id and category.website_id.id != website.id:
            return request.redirect('/shop')
        subcategories = request.env['product.public.category'].sudo().search([
            ('parent_id', '=', category.id),
            ('website_id', '=', website.id),
        ], order='sequence asc, name asc')
        cat_ids = [category.id] + subcategories.ids
        products = request.env['product.template'].sudo().search([
            ('is_published', '=', True),
            ('public_categ_ids', 'in', cat_ids),
        ], order='create_date desc')
        return request.render('web_trofeos.tr_category_page', {
            'category': category,
            'subcategories': subcategories,
            'products': products,
            'slug': slug,
        })

from odoo import http
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug


class TrofeosSite(http.Controller):

    @http.route(['/trofeos'], type='http', auth='public', website=True, sitemap=True)
    def home(self, **kw):
        return request.render('web_trofeos.tr_home')

    @http.route(['/quienes-somos-trofeos'], type='http', auth='public', website=True, sitemap=True)
    def quienes_somos(self, **kw):
        return request.render('web_trofeos.tr_quienes_somos_page')

    @http.route(['/servicios-trofeos'], type='http', auth='public', website=True, sitemap=True)
    def servicios(self, **kw):
        return request.render('web_trofeos.tr_servicios_page')

    @http.route(['/empresas-trofeos'], type='http', auth='public', website=True, sitemap=True)
    def empresas(self, **kw):
        return request.render('web_trofeos.tr_empresas_page')

    @http.route(['/contacto-trofeos'], type='http', auth='public', website=True, sitemap=True)
    def contacto(self, **kw):
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

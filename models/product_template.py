from odoo import models
from odoo.exceptions import AccessError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _compute_can_publish(self):
        """Allow publishing products whose company matches the current website's company.

        Odoo's default implementation calls check_access_rule('write') using the
        user's active session companies (company_ids). When a product belongs to a
        company that is not active in the user's session (e.g. the user has
        company_id=1 active but the product has company_id=47), the ir.rule
        "Product multi-company" blocks the write check and can_publish becomes False.

        Fix: if the product's company matches the current website's company, evaluate
        the write check inside a with_company() context so the ir.rule sees the
        correct company in company_ids.
        """
        website = self.env['website'].get_current_website() if self.env.context.get('website_id') else None
        if not website:
            try:
                website = self.env['website'].get_current_website()
            except Exception:
                website = None

        for record in self:
            product_company = record.company_id
            if website and product_company and product_company == website.company_id:
                try:
                    plain = record.with_company(product_company).sudo(flag=False)
                    plain.check_access_rights('write')
                    plain.check_access_rule('write')
                    record.can_publish = True
                except AccessError:
                    record.can_publish = False
            else:
                try:
                    plain_record = record.sudo(flag=False) if self._context.get('can_publish_unsudo_main_object', False) else record
                    plain_record.check_access_rights('write')
                    plain_record.check_access_rule('write')
                    record.can_publish = True
                except AccessError:
                    record.can_publish = False

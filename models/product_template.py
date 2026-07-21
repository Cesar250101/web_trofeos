import re

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import AccessError

# Etiquetas que identifican una fila de dimensión (columna izquierda de la tabla)
_DIM_LABELS = {
    'altura', 'alto', 'diametro', 'diámetro', 'diam', 'diám', 'ancho', 'largo',
    'fondo', 'espesor', 'profundidad', 'peso', 'medida', 'medidas',
}
# Etiquetas que introducen la fila de encabezado (tamaños/modelos)
_SIZE_LABELS = {'tamaño', 'tamano', 'modelo', 'talla', 'formato'}


def _blocks(text):
    """Divide el texto en bloques separados por líneas en blanco."""
    out = []
    for part in re.split(r'\n\s*\n', text.strip()):
        lines = [ln.strip() for ln in part.split('\n') if ln.strip()]
        if lines:
            out.append(lines)
    return out


def _norm_label(s):
    return s.rstrip(':').strip().lower()


def _looks_like_sizes(vals):
    """True si los valores parecen etiquetas cortas de tamaño (A, A+, B, C, 1…)."""
    return bool(vals) and all(len(v) <= 4 for v in vals)


def _nl2br(text):
    return Markup('<br/>').join(escape(line) for line in text.split('\n'))


def build_web_description(text, product_name):
    """Devuelve HTML confiable (Markup).

    Si ``description_sale`` sigue el patrón columnar de dimensiones
    (Tamaño → A/B/C, Altura → …, Diámetro → …) lo renderiza como tabla;
    en cualquier otro caso hace fallback a texto con saltos de línea,
    idéntico al render anterior.
    """
    text = (text or '').strip()
    if not text:
        return Markup('')

    size_header = None
    dim_rows = []           # [(label, [valores])]
    notes = []              # líneas de nota (empiezan con *)
    extra = []              # otras líneas de texto real a preservar

    for b in _blocks(text):
        label = _norm_label(b[0])

        if label in _SIZE_LABELS and len(b) >= 2:
            size_header = b[1:]
            continue
        if label in _DIM_LABELS and len(b) >= 2:
            dim_rows.append((b[0].rstrip(':').strip(), b[1:]))
            continue
        # variante: primer bloque = [código, s1, s2, …] con los tamaños en línea
        if size_header is None and len(b) >= 2 and label not in _DIM_LABELS \
                and _looks_like_sizes(b[1:]):
            size_header = b[1:]
            continue
        # resto: notas vs código suelto descartable vs texto real
        for ln in b:
            if ln.lstrip().startswith('*'):
                notes.append(ln.lstrip('* ').strip())
            elif len(b) == 1 and len(ln) <= 14 and not re.search(r'[.:,;]', ln):
                pass  # código suelto tipo "ET 172" / "109" → se descarta
            else:
                extra.append(ln)

    if not (size_header and dim_rows):
        return _nl2br(text)

    ncol = max(len(size_header), max(len(v) for _, v in dim_rows))
    header = list(size_header) + [''] * (ncol - len(size_header))

    parts = [u'<div class="tr-dim-table-wrap">',
             u'<table class="tr-dim-table">',
             u'<thead><tr>',
             u'<th class="tr-dim-corner">%s</th>' % escape(product_name or '')]
    for h in header:
        parts.append(u'<th>%s</th>' % escape(h))
    parts.append(u'</tr></thead><tbody>')
    for label, vals in dim_rows:
        vals = list(vals) + [''] * (ncol - len(vals))
        parts.append(u'<tr><th class="tr-dim-rowlabel">%s</th>' % escape(label.upper()))
        for v in vals:
            parts.append(u'<td>%s</td>' % escape(v))
        parts.append(u'</tr>')
    parts.append(u'</tbody></table>')

    for ln in extra:
        parts.append(u'<p class="tr-dim-extra">%s</p>' % escape(ln))
    for ln in notes:
        parts.append(u'<p class="tr-dim-note">%s</p>' % escape(ln))
    parts.append(u'</div>')

    return Markup(''.join(parts))


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tr_web_description = fields.Html(
        string='Descripción web (tabla)',
        compute='_compute_tr_web_description',
        sanitize=False,
        store=False,
        help='HTML derivado de description_sale: convierte el listado columnar '
             'de dimensiones en una tabla; el resto se muestra como texto.',
    )

    @api.depends('description_sale', 'name')
    def _compute_tr_web_description(self):
        for rec in self:
            rec.tr_web_description = build_web_description(
                rec.description_sale or '', rec.name or '')

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

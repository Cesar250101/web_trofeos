import logging
import re

import requests

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

_WP_ADMIN_URL  = 'https://www.trofeospremiumsspa.cl/wp/wp-admin'
_WP_LOGIN_URL  = 'https://www.trofeospremiumsspa.cl/wp/wp-login.php'
_WP_ADMIN_USER = 'premiums'
_WP_ADMIN_PASS = 'Cx%Myz&dDOB*nZIO'
_SKIP_SLUGS    = {'uncategorized', 'sin-categoria'}

# --- Credenciales REST WooCommerce (fallback si res.company no las tiene) ---
_WC_URL     = 'https://www.trofeospremiums.cl/wp/'
_WC_KEY     = 'ck_e196d979581f268f27ef8ad483ebc21d550cec38'
_WC_SECRET  = 'cs_2719b42fef33b43eb62cd8c20b16450beb9e130d'
_WC_VERSION = 'wc/v3'
_TROFEOS_COMPANY_ID = 47


def _wp_admin_session():
    try:
        from bs4 import BeautifulSoup as _BS
    except ImportError:
        _BS = None
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (web_trofeos Odoo sync)'})
    try:
        session.get(_WP_LOGIN_URL, timeout=20)
        session.post(_WP_LOGIN_URL, data={
            'log': _WP_ADMIN_USER,
            'pwd': _WP_ADMIN_PASS,
            'wp-submit': 'Log+In',
            'redirect_to': '/wp/wp-admin/',
            'testcookie': '1',
        }, timeout=20, allow_redirects=True)
    except Exception as exc:
        _logger.warning('web_trofeos: no se pudo autenticar en WP admin: %s', exc)
        return None, None
    return session, _BS


def _fetch_via_wp_admin():
    session, BS = _wp_admin_session()
    if not session:
        return []
    if BS is None:
        _logger.warning('web_trofeos: beautifulsoup4 no está instalado.')
        return []

    seen_slugs = {}
    page = 1
    prev_rows = None

    while True:
        url = _WP_ADMIN_URL + '/edit-tags.php?taxonomy=product_cat&post_type=product' + f'&paged={page}'
        try:
            r = session.get(url, timeout=20)
        except Exception as exc:
            _logger.warning('web_trofeos: error al obtener página %d: %s', page, exc)
            break

        soup = BS(r.text, 'html.parser')
        rows = soup.select('table.wp-list-table tbody tr')
        if not rows or rows == prev_rows:
            break
        prev_rows = rows

        raw_page = []
        for row in rows:
            name_el = row.select_one('.column-name a.row-title')
            slug_el = row.select_one('.column-slug')
            href    = name_el.get('href', '') if name_el else ''
            m       = re.search(r'tag_ID=(\d+)', href)
            term_id = int(m.group(1)) if m else None
            if not name_el or not term_id:
                continue
            raw_name = name_el.get_text(strip=True)
            depth, display = 0, raw_name
            while display.startswith('—'):
                display = display[1:].strip()
                depth += 1
            slug = slug_el.get_text(strip=True) if slug_el else display.lower()
            if slug in _SKIP_SLUGS:
                continue
            raw_page.append({'id': term_id, 'name': display, 'slug': slug, 'depth': depth, 'parent': 0})

        parent_stack = []
        for cat in raw_page:
            while parent_stack and parent_stack[-1][0] >= cat['depth']:
                parent_stack.pop()
            cat['parent'] = parent_stack[-1][1] if parent_stack else 0
            parent_stack.append((cat['depth'], cat['id']))
            if cat['slug'] not in seen_slugs:
                cat['menu_order'] = len(seen_slugs) * 10
                seen_slugs[cat['slug']] = cat

        if not soup.select_one('.tablenav-pages a.next-page'):
            break
        page += 1

    result = list(seen_slugs.values())
    _logger.info('web_trofeos: WP admin scraping → %d categorías', len(result))
    return result


def _get_wp_categories(env):
    cats = _fetch_via_wp_admin()
    if not cats:
        _logger.error('web_trofeos: No se pudieron obtener categorías desde WP admin.')
    return cats


def _get_premium_svg(name):
    import base64, unicodedata
    def _norm(s):
        return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower().strip()
    name_norm = _norm(name)
    cup_path = "M 32,22 h 36 v 22 c 0,10 -8,18 -18,18 c -10,0 -18,-8 -18,-22 Z M 40,62 h 20 M 50,44 v 18 M 32,28 h -7 c -4,0 -5,3 -5,7 v 6 c 0,4 2,6 5,6 h 7 M 68,28 h 7 c 4,0 5,3 5,7 v 6 c 0,4 -2,6 -5,6 h -7 M 36,72 h 28"
    trophy_path = "M 50,14 L 54,23 L 63,23 L 56,29 L 59,38 L 50,32 L 41,38 L 44,29 L 37,23 L 46,23 Z M 35,46 h 30 L 58,62 H 42 Z M 42,62 L 38,72 h 24 L 58,62 M 32,72 h 36"
    medal_path = "M 35,15 L 45,35 M 65,15 L 55,35 M 30,15 H 70 M 50,52 c 10,0 18,-8 18,-18 s -8,-18 -18,-18 s -18,8 -18,18 s 8,18 18,18 Z M 50,24 L 53,31 L 60,31 L 55,35 L 57,42 L 50,38 L 43,42 L 45,35 L 40,31 L 47,31 Z"
    wood_path = "M 28,18 h 44 v 22 c 0,16 -12,26 -22,30 c -10,-4 -22,-14 -22,-30 Z M 34,24 h 32 v 16 c 0,11 -8,18 -16,21 c -8,-3 -16,-10 -16,-21 Z"
    crystal_path = "M 50,15 L 75,34 L 66,70 L 34,70 L 25,34 Z M 50,15 L 50,70 M 25,34 L 75,34 M 34,70 L 50,15 L 66,70"
    sublimation_path = "M 32,20 h 26 c 4,0 6,2 6,6 v 32 c 0,4 -2,6 -6,6 H 32 c -4,0 -6,-2 -6,-6 V 26 c 0,-4 2,-6 6,-6 Z M 64,28 h 6 c 3,0 5,2 5,5 v 10 c 0,3 -2,5 -5,5 h -6 M 34,14 h 22 M 38,10 h 14"
    print_path = "M 32,20 h 36 v 22 H 32 Z M 50,42 v 10 M 42,56 a 3,3 0 1 0 6,0 a 3,3 0 1 0 -6,0 Z M 54,62 a 4,4 0 1 0 8,0 a 4,4 0 1 0 -8,0 Z M 34,64 a 2,2 0 1 0 4,0 a 2,2 0 1 0 -4,0 Z"
    insumos_path = "M 50,36 a 12,12 0 1 0 0,24 a 12,12 0 1 0 0,-24 Z M 50,14 v 8 M 50,70 v 8 M 22,48 h 8 M 70,48 h 8 M 30,28 L 36,34 M 64,62 L 70,68 M 30,68 L 36,62 M 64,34 L 70,28"
    licenciatura_path = "M 18,36 L 50,20 L 82,36 L 50,52 Z M 50,52 v 16 c 0,6 -6,10 -18,10 M 72,41 v 18 c 0,2 1,3 3,3"
    patrias_path = "M 50,15 L 61,36 L 85,36 L 66,50 L 73,73 L 50,58 L 27,73 L 34,50 L 15,36 L 39,36 Z"
    deportes_path = "M 50,18 a 30,30 0 1 0 0,60 a 30,30 0 1 0 0,-60 Z M 50,18 v 60 M 20,48 h 60 M 29,27 L 71,69 M 29,69 L 71,27"
    cinta_path = "M 32,70 L 42,42 L 50,50 L 58,42 L 68,70 L 58,62 L 50,70 L 42,62 Z M 50,15 c 10,0 18,8 18,18 s -8,18 -18,18 s -18,-8 -18,-18 s 8,-18 18,-18 Z"
    acrylic_path = "M 30,20 L 70,20 L 60,68 L 40,68 Z M 22,68 h 56 v 6 h -56 Z M 40,20 L 45,68 M 60,20 L 55,68 M 50,20 L 50,68"
    themes = {
        'copa': ('#FFD700','#FF8C00',cup_path), 'juego': ('#FFD700','#FF8C00',cup_path),
        'trofeo': ('#FFE066','#F3A812',trophy_path),
        'medal': ('#FF9933','#FFCC00',medal_path), 'porta medal': ('#FF9933','#FFCC00',medal_path),
        'madera': ('#CD853F','#8B4513',wood_path), 'galvano': ('#CD853F','#8B4513',wood_path), 'regalo': ('#CD853F','#8B4513',wood_path),
        'cristal': ('#00E5FF','#0066FF',crystal_path),
        'sublim': ('#E040FB','#6200EA',sublimation_path),
        'impresion': ('#FF007F','#00F5FF',print_path), 'color': ('#FF007F','#00F5FF',print_path),
        'insum': ('#90A4AE','#37474F',insumos_path), 'maquin': ('#90A4AE','#37474F',insumos_path),
        'licencia': ('#2196F3','#0D47A1',licenciatura_path), 'gradua': ('#2196F3','#0D47A1',licenciatura_path),
        'patria': ('#0039A6','#D52B1E',patrias_path),
        'deport': ('#00E676','#1B5E20',deportes_path), 'futbol': ('#00E676','#1B5E20',deportes_path),
        'cinta': ('#FF1744','#D50000',cinta_path),
        'plastic': ('#00E5FF','#1DE9B6',acrylic_path), 'acril': ('#00E5FF','#1DE9B6',acrylic_path), 'resin': ('#FFE066','#F3A812',trophy_path),
    }
    color1, color2, path = '#FFD700', '#FF8C00', cup_path
    for kw, theme in themes.items():
        if kw in name_norm:
            color1, color2, path = theme
            break
    svg_code = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="800" height="800"><defs><linearGradient id="pg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:{color1}"/><stop offset="100%" style="stop-color:{color2}"/></linearGradient><radialGradient id="bg" cx="50%" cy="40%" r="60%"><stop offset="0%" style="stop-color:#1E222A"/><stop offset="100%" style="stop-color:#0B0C10"/></radialGradient><filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feComposite in="SourceGraphic" in2="blur" operator="over"/></filter></defs><rect width="100" height="100" fill="url(#bg)" rx="16"/><g transform="translate(0,-4)" filter="url(#glow)"><path d="{path}" fill="none" stroke="url(#pg)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></g><rect x="10" y="76" width="80" height="14" fill="#FFFFFF" fill-opacity="0.04" rx="7"/><text x="50" y="85" fill="#F3F4F6" font-family="sans-serif" font-size="5" font-weight="800" text-anchor="middle" letter-spacing="1.2">{name.upper()}</text></svg>'
    return base64.b64encode(svg_code.encode('utf-8')).decode('utf-8')


def _sync_categories(env, website):
    Cat = env['product.public.category']
    wp_cats = _get_wp_categories(env)
    if not wp_cats:
        return
    existing = Cat.search([('website_id', '=', website.id)])
    slug_to_odoo = {}
    for rec in existing:
        slug = getattr(rec, 'website_slug', None) or re.sub(r'\s+', '-', rec.name.lower())
        slug_to_odoo[slug] = rec
    name_to_odoo = {rec.name.strip().lower(): rec for rec in existing}
    wp_to_odoo = {}
    ordered = sorted(wp_cats, key=lambda c: (c.get('depth', 0), c.get('menu_order', 0), c['id']))
    created = skipped = 0
    for wp_cat in ordered:
        slug, name, wp_id = wp_cat['slug'], wp_cat['name'], wp_cat['id']
        seq = wp_cat.get('menu_order', 0) or (len(wp_to_odoo) + 1) * 10
        odoo_rec = slug_to_odoo.get(slug) or name_to_odoo.get(name.strip().lower())
        if odoo_rec:
            wp_to_odoo[wp_id] = odoo_rec.id
            skipped += 1
            continue
        parent_odoo_id = wp_to_odoo.get(wp_cat.get('parent', 0))
        vals = {'name': name, 'website_id': website.id, 'sequence': seq, 'image_1920': _get_premium_svg(name)}
        if parent_odoo_id:
            vals['parent_id'] = parent_odoo_id
        new_rec = Cat.create(vals)
        wp_to_odoo[wp_id] = new_rec.id
        slug_to_odoo[slug] = new_rec
        name_to_odoo[name.lower()] = new_rec
        created += 1
    _logger.info('web_trofeos: categorías — %d creadas, %d ya existían.', created, skipped)


def _sync_menus(env, website):
    import unicodedata
    def _norm(s):
        return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower().strip()
    Menu = env['website.menu']
    Cat  = env['product.public.category']
    top_menu = website.menu_id
    if not top_menu:
        return
    for label, url, seq in [
        ('Inicio', '/trofeos', 5), ('Servicios', '/servicios-trofeos', 20),
        ('Empresas', '/empresas-trofeos', 30), ('Nosotros', '/quienes-somos-trofeos', 40),
        ('Contacto', '/contacto-trofeos', 99),
    ]:
        if not Menu.search([('website_id', '=', website.id), ('url', '=', url)], limit=1):
            Menu.create({'name': label, 'url': url, 'parent_id': top_menu.id, 'website_id': website.id, 'sequence': seq})
    Menu.search([('website_id', '=', website.id), '|', '|',
        ('url', 'like', '/shop?category='), ('url', 'like', '/coleccion-trofeos/'), ('url', '=', '#')]).unlink()
    all_cats = Cat.search([('website_id', '=', website.id)])
    def find_cat(target_norm):
        for c in all_cats:
            if _norm(c.name) == target_norm: return c
        for c in all_cats:
            if target_norm in _norm(c.name): return c
        return None
    def get_children(cat):
        return all_cats.filtered(lambda c: c.parent_id.id == cat.id).sorted('sequence')
    def make_menu(cat, parent_id, seq):
        m = Menu.create({'name': cat.name, 'url': '/shop?category=%d' % cat.id, 'parent_id': parent_id, 'website_id': website.id, 'sequence': seq})
        for j, child in enumerate(get_children(cat), 1):
            Menu.create({'name': child.name, 'url': '/shop?category=%d' % child.id, 'parent_id': m.id, 'website_id': website.id, 'sequence': j * 10})
        return m
    productos_menu = Menu.create({'name': 'Productos', 'url': '#', 'parent_id': top_menu.id, 'website_id': website.id, 'sequence': 50})
    for idx, kw in enumerate(['copas','trofeos','medallas','maderas','cristales','sublimacion','impresion directa color','insumos'], 1):
        cat = find_cat(kw)
        if cat: make_menu(cat, productos_menu.id, idx * 10)
        else: _logger.warning('web_trofeos: Categoría "%s" no encontrada para menú', kw)
    for idx, kw in enumerate(['licenciaturas','fiestas patrias','deportes'], 1):
        cat = find_cat(kw)
        if cat: make_menu(cat, top_menu.id, 60 + idx * 10)


# ======================================================================
# Sincronización de public_categ_ids desde WooCommerce (REST API)
# ----------------------------------------------------------------------
# A diferencia de _sync_categories (scraping WP admin, que sólo crea las
# product.public.category), esto usa la REST API oficial para:
#   1) mapear cada categoría WC a su product.public.category (keyed por
#      woo_category_id, backfilleando las ya creadas por nombre), y
#   2) asignar public_categ_ids a cada producto de Odoo emparejando por SKU
#      (default_code). Para productos WC "variable" el SKU vive en las
#      variaciones, así que se descargan y se mapean todas.
# ======================================================================

def _wc_norm_txt(s):
    import unicodedata
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower().strip()


def _get_wc_api(env):
    """Construye el cliente WooCommerce REST.

    Prefiere las credenciales de la compañía Trofeos (id=47); si faltan, usa
    las constantes del módulo. Normaliza woo_version (a veces mal configurado,
    p.ej. "V2") al formato válido ``wc/vN``.
    """
    try:
        from woocommerce import API
    except ImportError:
        _logger.error('web_trofeos: paquete "woocommerce" no instalado; no se puede sincronizar public_categ_ids.')
        return None

    company = env['res.company'].sudo().browse(_TROFEOS_COMPANY_ID)
    exists = company.exists()
    url     = (company.woo_url if exists else '') or _WC_URL
    key     = (company.woo_consumer_key if exists else '') or _WC_KEY
    secret  = (company.woo_consumer_secret if exists else '') or _WC_SECRET
    version = (company.woo_version if exists else '') or ''
    if not re.match(r'^wc/v\d+$', version or ''):
        version = _WC_VERSION

    return API(
        url=url,
        consumer_key=key,
        consumer_secret=secret,
        version=version,
        timeout=60,
        query_string_auth=True,
    )


def _wc_get_all(wcapi, endpoint, params=None):
    """Recorre todas las páginas de un endpoint WC (per_page=100)."""
    params = dict(params or {})
    params.setdefault('per_page', 100)
    results = []
    page = 1
    while True:
        params['page'] = page
        try:
            resp = wcapi.get(endpoint, params=params)
        except Exception as exc:
            _logger.warning('web_trofeos: error WC GET %s (page %d): %s', endpoint, page, exc)
            break
        if resp.status_code != 200:
            _logger.warning('web_trofeos: WC GET %s (page %d) status %s', endpoint, page, resp.status_code)
            break
        batch = resp.json()
        if not batch:
            break
        results.extend(batch)
        try:
            total_pages = int(resp.headers.get('X-WP-TotalPages', page))
        except (TypeError, ValueError):
            total_pages = page
        if page >= total_pages:
            break
        page += 1
    return results


def _sync_wc_categories_rest(env, website, wcapi):
    """Mapea las categorías WC → product.public.category (por woo_category_id).

    Devuelve dict ``{str(wc_cat_id): odoo_public_categ_id}``.
    """
    Cat = env['product.public.category']
    wc_cats = _wc_get_all(wcapi, 'products/categories')
    if not wc_cats:
        _logger.warning('web_trofeos: la REST API no devolvió categorías WC.')
        return {}

    existing = Cat.with_context(active_test=False).search([('website_id', '=', website.id)])
    by_woo_id = {c.woo_category_id: c for c in existing if c.woo_category_id}
    by_name   = {_wc_norm_txt(c.name): c for c in existing}

    # Ordenar padres antes que hijos para poder enlazar parent_id.
    idmap = {c['id']: c for c in wc_cats}

    def _depth(cat):
        d, cur, seen = 0, cat, set()
        while cur.get('parent') and cur['parent'] in idmap and cur['id'] not in seen:
            seen.add(cur['id'])
            cur = idmap[cur['parent']]
            d += 1
        return d

    wc_cats_sorted = sorted(wc_cats, key=lambda c: (_depth(c), c.get('menu_order', 0), c['id']))

    wc_id_to_odoo = {}
    created = updated = 0
    for wc in wc_cats_sorted:
        wc_id = str(wc['id'])
        name = (wc.get('name') or '').strip()
        if not name or wc.get('slug') in _SKIP_SLUGS:
            continue
        parent_odoo = wc_id_to_odoo.get(str(wc.get('parent') or '0'))
        rec = by_woo_id.get(wc_id) or by_name.get(_wc_norm_txt(name))
        if rec:
            upd = {}
            if rec.woo_category_id != wc_id:
                upd['woo_category_id'] = wc_id
            if parent_odoo and rec.parent_id.id != parent_odoo:
                upd['parent_id'] = parent_odoo
            if upd:
                rec.write(upd)
                updated += 1
        else:
            vals = {
                'name': name,
                'website_id': website.id,
                'woo_category_id': wc_id,
                'sequence': wc.get('menu_order', 0) or 0,
                'image_1920': _get_premium_svg(name),
            }
            if parent_odoo:
                vals['parent_id'] = parent_odoo
            rec = Cat.create(vals)
            created += 1
        wc_id_to_odoo[wc_id] = rec.id
        by_woo_id[wc_id] = rec
        by_name[_wc_norm_txt(name)] = rec

    _logger.info('web_trofeos: categorías WC (REST) — %d creadas, %d actualizadas, %d mapeadas.',
                 created, updated, len(wc_id_to_odoo))
    return wc_id_to_odoo


def _sync_wc_product_public_categs(env, website, wcapi, wc_id_to_odoo):
    """Asigna public_categ_ids a los productos de Odoo según la categoría del
    producto en WooCommerce. Emparejamiento por SKU (default_code).
    """
    if not wc_id_to_odoo:
        _logger.warning('web_trofeos: sin mapa de categorías WC; se omite asignación a productos.')
        return

    company_id = website.company_id.id or _TROFEOS_COMPANY_ID

    # Índice SKU -> product_tmpl_id, construido de una sola vez (variantes).
    ProductProduct = env['product.product']
    variants = ProductProduct.with_context(active_test=False).search([
        ('company_id', 'in', [company_id, False]),
        ('default_code', '!=', False),
    ])
    sku_to_tmpl = {}
    for v in variants:
        sku = (v.default_code or '').strip()
        if sku and sku not in sku_to_tmpl:
            sku_to_tmpl[sku] = v.product_tmpl_id.id
    _logger.info('web_trofeos: índice de %d SKU de Odoo (compañía %s).', len(sku_to_tmpl), company_id)

    products = _wc_get_all(wcapi, 'products')
    total = len(products)
    _logger.info('web_trofeos: %d productos WC a procesar.', total)

    # Acumular tmpl_id -> set(odoo_public_categ_id) (unión si varios coinciden).
    tmpl_categs = {}
    for i, p in enumerate(products, 1):
        odoo_categ_ids = {
            wc_id_to_odoo[str(c.get('id'))]
            for c in (p.get('categories') or [])
            if str(c.get('id')) in wc_id_to_odoo
        }
        if not odoo_categ_ids:
            continue

        skus = set()
        top_sku = (p.get('sku') or '').strip()
        if top_sku:
            skus.add(top_sku)
        if p.get('type') == 'variable':
            for var in _wc_get_all(wcapi, 'products/%s/variations' % p['id']):
                vsku = (var.get('sku') or '').strip()
                if vsku:
                    skus.add(vsku)

        for sku in skus:
            tmpl_id = sku_to_tmpl.get(sku)
            if tmpl_id:
                tmpl_categs.setdefault(tmpl_id, set()).update(odoo_categ_ids)

        if i % 50 == 0:
            _logger.info('web_trofeos: %d/%d productos WC procesados...', i, total)

    Template = env['product.template']
    written = 0
    for tmpl_id, categ_ids in tmpl_categs.items():
        try:
            Template.browse(tmpl_id).write({'public_categ_ids': [(6, 0, list(categ_ids))]})
            written += 1
        except Exception as exc:
            _logger.warning('web_trofeos: no se pudo asignar public_categ_ids al template %s: %s', tmpl_id, exc)
    _logger.info('web_trofeos: public_categ_ids asignado a %d productos (%d productos WC sin match por SKU).',
                 written, total - len(tmpl_categs))


def _sync_woo_public_categs(env, website):
    """Orquesta el sync REST: categorías WC + asignación de public_categ_ids."""
    wcapi = _get_wc_api(env)
    if not wcapi:
        return
    wc_id_to_odoo = _sync_wc_categories_rest(env, website, wcapi)
    _sync_wc_product_public_categs(env, website, wcapi, wc_id_to_odoo)


def _fix_company_access(env, website):
    TROFEOS_COMPANY_ID = 47
    company = env['res.company'].sudo().browse(TROFEOS_COMPANY_ID)
    if not company.exists():
        _logger.warning('web_trofeos: Compañía id=47 no encontrada.')
        return
    if website.company_id.id != TROFEOS_COMPANY_ID:
        website.sudo().write({'company_id': TROFEOS_COMPANY_ID})
    for xmlid in ['base.group_system', 'website.group_website_publisher', 'website.group_website_designer']:
        try:
            group = env.ref(xmlid, raise_if_not_found=False)
            if not group: continue
            for user in group.users:
                if company not in user.company_ids:
                    user.sudo().write({'company_ids': [(4, TROFEOS_COMPANY_ID)]})
        except Exception:
            pass
    public_user = website.user_id
    if public_user and company not in public_user.company_ids:
        public_user.sudo().write({'company_ids': [(4, TROFEOS_COMPANY_ID)]})
    _set_website_logo(env, website)


def _set_website_logo(env, website):
    """Upload logo.svg from static/src/img/ as the website logo (always overwrites)."""
    import base64, os
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'src', 'img', 'logo.svg')
    if not os.path.exists(logo_path):
        _logger.warning('web_trofeos: logo.svg no encontrado en %s', logo_path)
        return
    with open(logo_path, 'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    website.sudo().write({'logo': logo_b64})
    _logger.info('web_trofeos: logo.svg configurado en sitio "%s".', website.name)


def _run_sync(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    if not website:
        _logger.warning('web_trofeos: No se encontró el sitio "Trofeos". Hook omitido.')
        return
    _fix_company_access(env, website)
    _sync_categories(env, website)
    _sync_menus(env, website)
    try:
        _sync_woo_public_categs(env, website)
    except Exception as exc:  # nunca abortar el upgrade por la API externa
        _logger.exception('web_trofeos: fallo en sync WooCommerce → public_categ_ids: %s', exc)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    if not website:
        return
    lang = (env['res.lang'].search([('code', '=', 'es_CL')], limit=1)
            or env['res.lang'].search([('code', '=', 'es')], limit=1))
    vals = {'homepage_url': '/trofeos'}
    if lang:
        vals['language_ids'] = [(6, 0, [lang.id])]
        vals['default_lang_id'] = lang.id
    website.write(vals)
    _fix_company_access(env, website)
    _sync_categories(env, website)
    _sync_menus(env, website)
    try:
        _sync_woo_public_categs(env, website)
    except Exception as exc:
        _logger.exception('web_trofeos: fallo en sync WooCommerce → public_categ_ids: %s', exc)


def post_update_hook(cr, registry):
    _run_sync(cr, registry)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    if website:
        env['product.public.category'].search([('website_id', '=', website.id)]).unlink()

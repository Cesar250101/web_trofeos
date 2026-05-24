import logging
import re

import requests

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# ─── WooCommerce REST API ─────────────────────────────────────────────────────
# Credentials are read (in priority order) from:
#   1. res.company fields: woo_url, woo_consumer_key, woo_consumer_secret, woo_version
#      (company linked to website "Trofeos", or the first company with woo_integrar=True)
#   2. Odoo System Parameters: web_trofeos.wc_url / wc_key / wc_secret / wc_version
#   3. Hardcoded fallback defaults (used as last resort)

_WC_DEFAULTS = {
    'url':     'https://www.trofeospremiumsspa.cl/wp',
    'key':     '',
    'secret':  '',
    'version': 'v2',
}


# ─── Category fetch helpers ───────────────────────────────────────────────────

def _wc_config(env):
    """Read WooCommerce credentials from res.company, then ir.config_parameter."""
    # 1. Try res.company for the company linked to website Trofeos
    Company = env['res.company'].sudo()
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    company = None
    if website and website.company_id:
        company = website.company_id
    if not company:
        # Fallback: first company with WC integration enabled
        company = Company.search([('woo_integrar', '=', True)], limit=1)
    if company and company.woo_consumer_key and company.woo_consumer_secret:
        raw_version = (company.woo_version or 'V2').strip().lower().lstrip('v')
        return {
            'url':     (company.woo_url or _WC_DEFAULTS['url']).rstrip('/'),
            'key':     company.woo_consumer_key,
            'secret':  company.woo_consumer_secret,
            'version': 'v' + raw_version,
        }
    # 2. Fallback to ir.config_parameter
    ICP = env['ir.config_parameter'].sudo()
    return {
        'url':     ICP.get_param('web_trofeos.wc_url',     _WC_DEFAULTS['url']).rstrip('/'),
        'key':     ICP.get_param('web_trofeos.wc_key',     _WC_DEFAULTS['key']),
        'secret':  ICP.get_param('web_trofeos.wc_secret',  _WC_DEFAULTS['secret']),
        'version': ICP.get_param('web_trofeos.wc_version', _WC_DEFAULTS['version']),
    }


def _fetch_via_wc_api(cfg):
    """
    Primary: WooCommerce REST API (version read from res.company, default v2).
    Returns list of raw dicts or [] on failure.
    Fetches all pages (100 per page) to handle large category trees.
    """
    version = cfg.get('version', 'v2')
    base_url = cfg['url'] + '/wp-json/wc/' + version + '/products/categories'
    all_cats = []
    page = 1
    try:
        while True:
            resp = requests.get(
                base_url,
                params={'per_page': 100, 'page': page, 'hide_empty': 'false'},
                auth=(cfg['key'], cfg['secret']),
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if not data:
                    break
                all_cats.extend(data)
                if len(data) < 100:
                    break
                page += 1
            else:
                _logger.warning(
                    'web_trofeos: WC API HTTP %s — %s',
                    resp.status_code, resp.text[:300],
                )
                return []
        _logger.info('web_trofeos: WC API OK -> %d categorias', len(all_cats))
        return all_cats
    except Exception as exc:
        _logger.warning('web_trofeos: WC API error: %s', exc)
    return []


def _fetch_via_html_scraping(cfg):
    """
    Fallback: parse public WooCommerce category pages from the nav/shop sidebar.
    Builds a flat+hierarchy list using /product-category/ URL patterns.
    Returns same format as the WC API (id, name, slug, parent, menu_order).
    """
    base = cfg['url']
    cats_by_slug = {}   # slug → {id, name, slug, parent_slug, menu_order}
    fake_id = 1

    def _scrape_page(url):
        nonlocal fake_id
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200:
                return
            html = r.text
            # Grab all /product-category/SLUG/ hrefs with their anchor text
            pattern = (
                r'href=["\']' + re.escape(base) +
                r'/product-category/([^/"\']+)/["\'][^>]*>\s*([^<]+?)\s*<'
            )
            for slug, name in re.findall(pattern, html):
                name = re.sub(r'\s+', ' ', name).strip()
                if slug not in cats_by_slug and name:
                    cats_by_slug[slug] = {
                        'id': fake_id,
                        'name': name,
                        'slug': slug,
                        'parent': 0,
                        'menu_order': fake_id * 10,
                        '_parent_slug': None,
                    }
                    fake_id += 1
        except Exception as exc:
            _logger.debug('web_trofeos: scraping %s: %s', url, exc)

    # Scrape main shop and home pages
    _scrape_page(base + '/shop/')
    _scrape_page(base + '/')

    # Scrape each known category page to find subcategories
    for slug in list(cats_by_slug.keys()):
        cat_url = base + '/product-category/' + slug + '/'
        before = set(cats_by_slug.keys())
        _scrape_page(cat_url)
        new_slugs = set(cats_by_slug.keys()) - before
        for new_slug in new_slugs:
            cats_by_slug[new_slug]['parent'] = cats_by_slug[slug]['id']

    skip = {'uncategorized', 'sin-categoria'}
    result = [c for c in cats_by_slug.values() if c['slug'] not in skip]
    _logger.info('web_trofeos: scraping → %d categorías', len(result))
    return result


def _get_wp_categories(env):
    """Try WC REST API first; fall back to HTML scraping."""
    cfg = _wc_config(env)
    cats = _fetch_via_wc_api(cfg)
    if not cats:
        _logger.info('web_trofeos: WC API no disponible, usando scraping HTML.')
        cats = _fetch_via_html_scraping(cfg)
    return cats


# ─── SVG Image Generation Helper ──────────────────────────────────────────────

def _get_premium_svg(name):
    """
    Generates a premium high-quality glassmorphic SVG card representing the category.
    Returns base64 encoded string.
    """
    import base64
    import unicodedata

    def _norm(s):
        return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower().strip()

    name_norm = _norm(name)

    # 1. Copas / Cups (Golden/Yellow Amber glow)
    cup_path = "M 32,22 h 36 v 22 c 0,10 -8,18 -18,18 c -10,0 -18,-8 -18,-22 Z M 40,62 h 20 M 50,44 v 18 M 32,28 h -7 c -4,0 -5,3 -5,7 v 6 c 0,4 2,6 5,6 h 7 M 68,28 h 7 c 4,0 5,3 5,7 v 6 c 0,4 -2,6 -5,6 h -7 M 36,72 h 28"
    cup_theme = ('#FFD700', '#FF8C00', cup_path)

    # 2. Trofeos / Trophies (Bright Gold/Sun glow)
    trophy_path = "M 50,14 L 54,23 L 63,23 L 56,29 L 59,38 L 50,32 L 41,38 L 44,29 L 37,23 L 46,23 Z M 35,46 h 30 L 58,62 H 42 Z M 42,62 L 38,72 h 24 L 58,62 M 32,72 h 36"
    trophy_theme = ('#FFE066', '#F3A812', trophy_path)

    # 3. Medallas / Medals (Orange Gold/Bronze warmth)
    medal_path = "M 35,15 L 45,35 M 65,15 L 55,35 M 30,15 H 70 M 50,52 c 10,0 18,-8 18,-18 s -8,-18 -18,-18 s -18,8 -18,18 s 8,18 18,18 Z M 50,24 L 53,31 L 60,31 L 55,35 L 57,42 L 50,38 L 43,42 L 45,35 L 40,31 L 47,31 Z"
    medal_theme = ('#FF9933', '#FFCC00', medal_path)

    # 4. Maderas / Wood awards (Warm mahogany/amber)
    wood_path = "M 28,18 h 44 v 22 c 0,16 -12,26 -22,30 c -10,-4 -22,-14 -22,-30 Z M 34,24 h 32 v 16 c 0,11 -8,18 -16,21 c -8,-3 -16,-10 -16,-21 Z"
    wood_theme = ('#CD853F', '#8B4513', wood_path)

    # 5. Cristales / Crystals (Cyan/Electric Ice Blue)
    crystal_path = "M 50,15 L 75,34 L 66,70 L 34,70 L 25,34 Z M 50,15 L 50,70 M 25,34 L 75,34 M 34,70 L 50,15 L 66,70"
    crystal_theme = ('#00E5FF', '#0066FF', crystal_path)

    # 6. Sublimacion / Sublimation (Neon Purple/Indigo)
    sublimation_path = "M 32,20 h 26 c 4,0 6,2 6,6 v 32 c 0,4 -2,6 -6,6 H 32 c -4,0 -6,-2 -6,-6 V 26 c 0,-4 2,-6 6,-6 Z M 64,28 h 6 c 3,0 5,2 5,5 v 10 c 0,3 -2,5 -5,5 h -6 M 34,14 h 22 M 38,10 h 14"
    sublimation_theme = ('#E040FB', '#6200EA', sublimation_path)

    # 7. Impresion / Print (Rainbow CMYK Spectrum)
    print_path = "M 32,20 h 36 v 22 H 32 Z M 50,42 v 10 M 42,56 a 3,3 0 1 0 6,0 a 3,3 0 1 0 -6,0 Z M 54,62 a 4,4 0 1 0 8,0 a 4,4 0 1 0 -8,0 Z M 34,64 a 2,2 0 1 0 4,0 a 2,2 0 1 0 -4,0 Z"
    print_theme = ('#FF007F', '#00F5FF', print_path)

    # 8. Insumos / Accesorios / Supplies (Chrome/Slate Silver)
    insumos_path = "M 50,36 a 12,12 0 1 0 0,24 a 12,12 0 1 0 0,-24 Z M 50,14 v 8 M 50,70 v 8 M 22,48 h 8 M 70,48 h 8 M 30,28 L 36,34 M 64,62 L 70,68 M 30,68 L 36,62 M 64,34 L 70,28"
    insumos_theme = ('#90A4AE', '#37474F', insumos_path)

    # 9. Licenciaturas / Graduation (Midnight Blue & Silver)
    licenciatura_path = "M 18,36 L 50,20 L 82,36 L 50,52 Z M 50,52 v 16 c 0,6 -6,10 -18,10 M 72,41 v 18 c 0,2 1,3 3,3"
    licenciatura_theme = ('#2196F3', '#0D47A1', licenciatura_path)

    # 10. Fiestas Patrias (Chilean Tricolor - Blue/White/Red)
    patrias_path = "M 50,15 L 61,36 L 85,36 L 66,50 L 73,73 L 50,58 L 27,73 L 34,50 L 15,36 L 39,36 Z"
    patrias_theme = ('#0039A6', '#D52B1E', patrias_path)

    # 11. Deportes / Sports (Vibrant Green/Athletic Gold)
    deportes_path = "M 50,18 a 30,30 0 1 0 0,60 a 30,30 0 1 0 0,-60 Z M 50,18 v 60 M 20,48 h 60 M 29,27 L 71,69 M 29,69 L 71,27"
    deportes_theme = ('#00E676', '#1B5E20', deportes_path)

    # 12. Cintas / Ribbons (Vibrant Crimson/Red Gold)
    cinta_path = "M 32,70 L 42,42 L 50,50 L 58,42 L 68,70 L 58,62 L 50,70 L 42,62 Z M 50,15 c 10,0 18,8 18,18 s -8,18 -18,18 s -18,-8 -18,-18 s 8,-18 18,-18 Z"
    cinta_theme = ('#FF1744', '#D50000', cinta_path)

    # 13. Plasticos / Acrylics / Resina (Translucent Cyan/Neon Lime)
    acrylic_path = "M 30,20 L 70,20 L 60,68 L 40,68 Z M 22,68 h 56 v 6 h -56 Z M 40,20 L 45,68 M 60,20 L 55,68 M 50,20 L 50,68"
    acrylic_theme = ('#00E5FF', '#1DE9B6', acrylic_path)

    # Default Fallback (Elegant Amber Gold)
    default_theme = ('#FFD700', '#FF8C00', cup_path)

    # Map keywords to themes
    theme = default_theme
    if 'copa' in name_norm or 'juego' in name_norm:
        theme = cup_theme
    elif 'trofeo' in name_norm:
        theme = trophy_theme
    elif 'medal' in name_norm or 'porta medal' in name_norm:
        theme = medal_theme
    elif 'madera' in name_norm or 'galvano' in name_norm or 'regalo' in name_norm:
        theme = wood_theme
    elif 'cristal' in name_norm:
        theme = crystal_theme
    elif 'sublim' in name_norm:
        theme = sublimation_theme
    elif 'impresion' in name_norm or 'color' in name_norm:
        theme = print_theme
    elif 'insum' in name_norm or 'maquin' in name_norm or 'aplic' in name_norm or 'plac' in name_norm or 'pin' in name_norm or 'pioch' in name_norm or 'sello' in name_norm or 'acces' in name_norm or 'pint' in name_norm:
        theme = insumos_theme
    elif 'licencia' in name_norm or 'gradua' in name_norm:
        theme = licenciatura_theme
    elif 'patria' in name_norm or '18 sep' in name_norm:
        theme = patrias_theme
    elif 'deport' in name_norm or 'futbol' in name_norm or 'padel' in name_norm or 'tenis' in name_norm or 'fut' in name_norm or 'lf' in name_norm or 'lfc' in name_norm or 'lf2p' in name_norm:
        theme = deportes_theme
    elif 'cinta' in name_norm:
        theme = cinta_theme
    elif 'plastic' in name_norm:
        theme = acrylic_theme
    elif 'acril' in name_norm:
        theme = acrylic_theme
    elif 'resin' in name_norm:
        theme = trophy_theme

    color1, color2, path = theme

    svg_code = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="800" height="800">
    <defs>
        <linearGradient id="primary_grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:{color1};stop-opacity:1" />
            <stop offset="100%" style="stop-color:{color2};stop-opacity:1" />
        </linearGradient>
        <radialGradient id="bg_grad" cx="50%" cy="40%" r="60%">
            <stop offset="0%" style="stop-color:#1E222A;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#0B0C10;stop-opacity:1" />
        </radialGradient>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
    </defs>
    <rect width="100" height="100" fill="url(#bg_grad)" rx="16" />
    <rect x="1.5" y="1.5" width="97" height="97" fill="none" stroke="url(#primary_grad)" stroke-width="1.5" stroke-opacity="0.15" rx="14.5" />
    <circle cx="50" cy="0" r="30" fill="url(#primary_grad)" opacity="0.08" filter="url(#glow)" />
    <g transform="translate(0, -4)" filter="url(#glow)">
        <path d="{path}" fill="none" stroke="url(#primary_grad)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
    </g>
    <rect x="10" y="76" width="80" height="14" fill="#FFFFFF" fill-opacity="0.04" rx="7" />
    <text x="50" y="85" fill="#F3F4F6" font-family="'Inter', 'Montserrat', 'Segoe UI', sans-serif" font-size="5" font-weight="800" text-anchor="middle" letter-spacing="1.2">{name.upper()}</text>
</svg>"""

    return base64.b64encode(svg_code.encode('utf-8')).decode('utf-8')


# ─── Sync functions ───────────────────────────────────────────────────────────

def _sync_categories(env, website):
    """
    Full sync of product.public.category from WooCommerce for the given website.

    Strategy:
      1. Fetch all categories from WP (API or scraping).
      2. Delete ALL existing product.public.category for this website.
      3. Recreate parents first, then children.
      4. Duplicate prevention: we always delete & recreate, so no duplicates.
    """
    Cat = env['product.public.category']

    wp_cats = _get_wp_categories(env)
    if not wp_cats:
        _logger.error(
            'web_trofeos: No se obtuvieron categorías de WooCommerce. '
            'Verifica la URL y las credenciales API en Ajustes → '
            'Parámetros del sistema (web_trofeos.wc_url / wc_key / wc_secret).'
        )
        return

    # Delete all existing categories for this website
    Cat.search([('website_id', '=', website.id)]).unlink()

    skip_slugs = {'uncategorized', 'sin-categoria'}
    parents  = [
        c for c in wp_cats
        if c.get('parent', 0) == 0 and c.get('slug', '') not in skip_slugs
    ]
    children = [c for c in wp_cats if c.get('parent', 0) != 0]

    wp_to_odoo = {}   # wp_category_id → new odoo category id

    for seq, wp_cat in enumerate(
        sorted(parents, key=lambda c: (c.get('menu_order', 0), c['id'])), 1
    ):
        rec = Cat.create({
            'name': wp_cat['name'],
            'website_id': website.id,
            'sequence': seq * 10,
            'image_1920': _get_premium_svg(wp_cat['name']),
        })
        wp_to_odoo[wp_cat['id']] = rec.id

    for seq, wp_cat in enumerate(
        sorted(children, key=lambda c: (c.get('menu_order', 0), c['id'])), 1
    ):
        parent_odoo_id = wp_to_odoo.get(wp_cat.get('parent'))
        rec = Cat.create({
            'name': wp_cat['name'],
            'parent_id': parent_odoo_id,
            'website_id': website.id,
            'sequence': seq * 10,
            'image_1920': _get_premium_svg(wp_cat['name']),
        })
        wp_to_odoo[wp_cat['id']] = rec.id

    _logger.info(
        'web_trofeos: %d categorías sincronizadas con imágenes de alta calidad (%d padres + %d hijas).',
        len(wp_to_odoo), len(parents), len(children),
    )


def _sync_menus(env, website):
    """
    Sync website.menu category items after _sync_categories().

    Menu structure:
      - Static menus (Inicio, Servicios, Empresas, Nosotros, Contacto)
      - "Productos" dropdown with: Copas, Trofeos, Medallas, Maderas, Cristales,
        Sublimación, IMPRESIÓN DIRECTA COLOR, Insumos — each with their subcategories
      - Top-level: Licenciaturas, Fiestas Patrias, Deportes — each with their subcategories
    """
    import unicodedata

    def _norm(s):
        """Normalize accents and lowercase for comparison."""
        return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower().strip()

    Menu = env['website.menu']
    Cat  = env['product.public.category']
    top_menu = website.menu_id
    if not top_menu:
        return

    # ── Static menus — create only if missing ─────────────────────────────
    for label, url, seq in [
        ('Inicio',    '/trofeos',               5),
        ('Servicios', '/servicios-trofeos',    20),
        ('Empresas',  '/empresas-trofeos',     30),
        ('Nosotros',  '/quienes-somos-trofeos', 40),
        ('Contacto',  '/contacto-trofeos',     99),
    ]:
        if not Menu.search([('website_id', '=', website.id), ('url', '=', url)], limit=1):
            Menu.create({
                'name': label,
                'url': url,
                'parent_id': top_menu.id,
                'website_id': website.id,
                'sequence': seq,
            })

    # ── Dynamic category menus — delete all, then recreate ────────────────
    Menu.search([
        ('website_id', '=', website.id),
        '|', '|',
        ('url', 'like', '/shop?category='),
        ('url', 'like', '/coleccion-trofeos/'),
        ('url', '=', '#'),
    ]).unlink()

    # All categories for this website (one query)
    all_cats = Cat.search([('website_id', '=', website.id)])

    def find_cat(target_norm):
        for c in all_cats:
            if _norm(c.name) == target_norm:
                return c
        for c in all_cats:
            if target_norm in _norm(c.name):
                return c
        return None

    def get_direct_children(cat):
        return all_cats.filtered(lambda c: c.parent_id.id == cat.id).sorted('sequence')

    def make_menu(cat, parent_menu_id, seq):
        """Create menu for cat, then create child menus for its direct children."""
        m = Menu.create({
            'name': cat.name,
            'url': '/shop?category=%d' % cat.id,
            'parent_id': parent_menu_id,
            'website_id': website.id,
            'sequence': seq,
        })
        for j, child in enumerate(get_direct_children(cat), 1):
            Menu.create({
                'name': child.name,
                'url': '/shop?category=%d' % child.id,
                'parent_id': m.id,
                'website_id': website.id,
                'sequence': j * 10,
            })
        return m

    # ── "Productos" parent dropdown (top-level, sequence=50) ──────────────
    # Categories listed under Productos in display order
    bajo_productos = [
        'copas',
        'trofeos',
        'medallas',
        'maderas',
        'cristales',
        'sublimacion',
        'impresion directa color',
        'insumos',
    ]

    productos_menu = Menu.create({
        'name': 'Productos',
        'url': '#',
        'parent_id': top_menu.id,
        'website_id': website.id,
        'sequence': 50,
    })

    for idx, name_norm in enumerate(bajo_productos, 1):
        cat = find_cat(name_norm)
        if not cat:
            _logger.warning('web_trofeos: Categoría "%s" no encontrada para menú', name_norm)
            continue
        make_menu(cat, productos_menu.id, idx * 10)

    # ── Remaining top-level menus ──────────────────────────────────────────
    for idx, name_norm in enumerate(['licenciaturas', 'fiestas patrias', 'deportes'], 1):
        cat = find_cat(name_norm)
        if not cat:
            continue
        make_menu(cat, top_menu.id, 60 + idx * 10)


# ─── Hook entry points ────────────────────────────────────────────────────────

def _run_sync(cr, registry):
    """Shared core used by post_init_hook and post_update_hook."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    if not website:
        _logger.warning('web_trofeos: No se encontró el sitio "Trofeos". Hook omitido.')
        return
    _sync_categories(env, website)
    _sync_menus(env, website)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    if not website:
        return
    # Configure website language/homepage on first install only
    lang = (
        env['res.lang'].search([('code', '=', 'es_CL')], limit=1)
        or env['res.lang'].search([('code', '=', 'es')], limit=1)
    )
    vals = {'homepage_url': '/trofeos'}
    if lang:
        vals['language_ids'] = [(6, 0, [lang.id])]
        vals['default_lang_id'] = lang.id
    website.write(vals)
    _sync_categories(env, website)
    _sync_menus(env, website)


def post_update_hook(cr, registry):
    """Re-syncs categories and menus on every module update."""
    _run_sync(cr, registry)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    if website:
        env['product.public.category'].search([('website_id', '=', website.id)]).unlink()


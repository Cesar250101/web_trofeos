import logging
import re

import requests

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# ─── WordPress admin credentials ────────────────────────────────────────────
# Categories are fetched from the WP admin panel (edit-tags.php).
# Credentials can be overridden via ir.config_parameter:
#   web_trofeos.wp_admin_url / wp_admin_user / wp_admin_pass


# ─── Category fetch helpers ──────────────────────────────────────────────

_WP_ADMIN_URL  = 'https://www.trofeospremiumsspa.cl/wp/wp-admin'
_WP_LOGIN_URL  = 'https://www.trofeospremiumsspa.cl/wp/wp-login.php'
_WP_ADMIN_USER = 'premiums'
_WP_ADMIN_PASS = 'Cx%Myz&dDOB*nZIO'
_SKIP_SLUGS    = {'uncategorized', 'sin-categoria'}


def _wp_admin_session():
    """Return an authenticated requests.Session against the WP admin."""
    try:
        from bs4 import BeautifulSoup as _BS  # noqa — only needed here
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
    """
    Scrape the WP admin category list (edit-tags.php) to get the full
    category tree with correct parent relationships.

    Returns a list of dicts: {id, name, slug, parent, menu_order}
    where id/parent are the real WP term_IDs.
    Duplicates (WP paginates the same parent row on multiple pages) are
    deduplicated by slug.
    """
    session, BS = _wp_admin_session()
    if not session:
        return []
    if BS is None:
        _logger.warning('web_trofeos: beautifulsoup4 no está instalado, no se puede hacer scraping de WP admin.')
        return []

    seen_slugs = {}   # slug → dict  (dedup across pages)
    page = 1
    prev_rows = None  # detect when WP stops paginating

    while True:
        url = (
            _WP_ADMIN_URL
            + '/edit-tags.php?taxonomy=product_cat&post_type=product'
            + f'&paged={page}'
        )
        try:
            r = session.get(url, timeout=20)
        except Exception as exc:
            _logger.warning('web_trofeos: error al obtener página %d de categorías: %s', page, exc)
            break

        soup = BS(r.text, 'html.parser')
        rows = soup.select('table.wp-list-table tbody tr')
        if not rows or rows == prev_rows:
            break
        prev_rows = rows

        raw_page = []
        for row in rows:
            name_el  = row.select_one('.column-name a.row-title')
            slug_el  = row.select_one('.column-slug')
            href     = name_el.get('href', '') if name_el else ''
            m        = re.search(r'tag_ID=(\d+)', href)
            term_id  = int(m.group(1)) if m else None

            if not name_el or not term_id:
                continue

            raw_name = name_el.get_text(strip=True)
            depth    = 0
            display  = raw_name
            while display.startswith('—'):
                display = display[1:].strip()
                depth  += 1

            slug = slug_el.get_text(strip=True) if slug_el else display.lower()
            if slug in _SKIP_SLUGS:
                continue

            raw_page.append({
                'id':     term_id,
                'name':   display,
                'slug':   slug,
                'depth':  depth,
                'parent': 0,   # resolved below
            })

        # Resolve parent from indentation depth within this page
        parent_stack = []  # [(depth, term_id)]
        for cat in raw_page:
            while parent_stack and parent_stack[-1][0] >= cat['depth']:
                parent_stack.pop()
            cat['parent'] = parent_stack[-1][1] if parent_stack else 0
            parent_stack.append((cat['depth'], cat['id']))

            if cat['slug'] not in seen_slugs:
                cat['menu_order'] = len(seen_slugs) * 10
                seen_slugs[cat['slug']] = cat

        next_link = soup.select_one('.tablenav-pages a.next-page')
        if not next_link:
            break
        page += 1

    result = list(seen_slugs.values())
    _logger.info('web_trofeos: WP admin scraping → %d categorías', len(result))
    return result


def _get_wp_categories(env):
    """Fetch categories from WP admin. Falls back to empty list on failure."""
    cats = _fetch_via_wp_admin()
    if not cats:
        _logger.error(
            'web_trofeos: No se pudieron obtener categorías desde WP admin (%s). '
            'Verifica credenciales en hooks.py (_WP_ADMIN_USER / _WP_ADMIN_PASS).',
            _WP_ADMIN_URL,
        )
    return cats


# ─── SVG Image Generation Helper ──────────────────────────────────────────────────────

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


# ─── Sync functions ───────────────────────────────────────────────────────────────

def _sync_categories(env, website):
    """
    Upsert product.public.category from WP admin for the given website.

    Strategy:
      - Fetch categories from WP admin (edit-tags.php) via authenticated scraping.
      - For each category (identified by slug):
          * If it already exists for this website → do nothing (preserve any
            manual edits made in Odoo).
          * If it does not exist → create it with the SVG image.
      - Parents are processed before children so parent_id FK is always valid.
      - Never deletes existing categories.
    """
    Cat = env['product.public.category']

    wp_cats = _get_wp_categories(env)
    if not wp_cats:
        return

    # Index existing categories by slug for fast lookup
    existing = Cat.search([('website_id', '=', website.id)])
    slug_to_odoo = {}   # slug → odoo record
    for rec in existing:
        slug = getattr(rec, 'website_slug', None) or re.sub(r'\s+', '-', rec.name.lower())
        slug_to_odoo[slug] = rec

    # Also index by name (lower-stripped) as fallback
    name_to_odoo = {rec.name.strip().lower(): rec for rec in existing}

    wp_to_odoo = {}   # wp term_id → odoo record id

    # Process parents first, then children (sorted by depth then menu_order)
    ordered = sorted(wp_cats, key=lambda c: (c.get('depth', 0), c.get('menu_order', 0), c['id']))

    created = 0
    skipped = 0

    for wp_cat in ordered:
        slug   = wp_cat['slug']
        name   = wp_cat['name']
        wp_id  = wp_cat['id']
        seq    = wp_cat.get('menu_order', 0) or (len(wp_to_odoo) + 1) * 10

        # Find existing record by slug or name
        odoo_rec = slug_to_odoo.get(slug) or name_to_odoo.get(name.strip().lower())

        if odoo_rec:
            wp_to_odoo[wp_id] = odoo_rec.id
            skipped += 1
            continue

        # Resolve parent
        parent_wp_id   = wp_cat.get('parent', 0)
        parent_odoo_id = wp_to_odoo.get(parent_wp_id)

        vals = {
            'name':       name,
            'website_id': website.id,
            'sequence':   seq,
            'image_1920': _get_premium_svg(name),
        }
        if parent_odoo_id:
            vals['parent_id'] = parent_odoo_id

        new_rec = Cat.create(vals)
        wp_to_odoo[wp_id]          = new_rec.id
        slug_to_odoo[slug]         = new_rec
        name_to_odoo[name.lower()] = new_rec
        created += 1

    _logger.info(
        'web_trofeos: categorías — %d creadas, %d ya existían (sin cambios).',
        created, skipped,
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

    # ── Static menus — create only if missing ───────────────────────────────────────────
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

    # ── Dynamic category menus — delete all, then recreate ────────────────────────
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

    # ── "Productos" parent dropdown (top-level, sequence=50) ──────────────────────
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

    # ── Remaining top-level menus ────────────────────────────────────────────────
    for idx, name_norm in enumerate(['licenciaturas', 'fiestas patrias', 'deportes'], 1):
        cat = find_cat(name_norm)
        if not cat:
            continue
        make_menu(cat, top_menu.id, 60 + idx * 10)


# ─── Company access fix ──────────────────────────────────────────────────────────────

def _fix_company_access(env, website):
    """
    Ensures the website 'Trofeos' has the correct company assigned (Trofeos Premiums Spa, id=47)
    and that all users who manage the website belong to that company.

    Root cause: Odoo's "Product multi-company" ir.rule restricts product.template
    records to company_ids active in the user's session. When a product belongs to
    company 47 but the user's session only has company 1 active, publishing raises 403.

    Fix: ensure the public user and manager users all belong to company 47, and that
    the website itself points to company 47.
    """
    TROFEOS_COMPANY_ID = 47

    company = env['res.company'].sudo().browse(TROFEOS_COMPANY_ID)
    if not company.exists():
        _logger.warning('web_trofeos: Compañía id=47 no encontrada, omitiendo fix de acceso.')
        return

    # Ensure the website points to the correct company
    if website.company_id.id != TROFEOS_COMPANY_ID:
        website.sudo().write({'company_id': TROFEOS_COMPANY_ID})
        _logger.info(
            'web_trofeos: website "%s" corregido a compañía "%s".',
            website.name, company.name,
        )

    # Ensure manager users belong to the Trofeos company
    manager_group_xmlids = [
        'base.group_system',
        'website.group_website_publisher',
        'website.group_website_designer',
    ]
    for xmlid in manager_group_xmlids:
        try:
            group = env.ref(xmlid, raise_if_not_found=False)
            if not group:
                continue
            for user in group.users:
                if company not in user.company_ids:
                    user.sudo().write({'company_ids': [(4, TROFEOS_COMPANY_ID)]})
                    _logger.info(
                        'web_trofeos: compañía "%s" agregada al usuario "%s".',
                        company.name, user.login,
                    )
        except Exception:
            pass

    # CRITICAL: the public user (anonymous visitors) must belong to the Trofeos
    # company so Odoo's api.companies check does not raise 403 Forbidden.
    public_user = website.user_id
    if public_user and company not in public_user.company_ids:
        public_user.sudo().write({'company_ids': [(4, TROFEOS_COMPANY_ID)]})
        _logger.info(
            'web_trofeos: compañía "%s" agregada al usuario público "%s" del sitio.',
            company.name, public_user.login,
        )


# ─── Hook entry points ───────────────────────────────────────────────────────────────

def _run_sync(cr, registry):
    """Shared core used by post_init_hook and post_update_hook."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    if not website:
        _logger.warning('web_trofeos: No se encontró el sitio "Trofeos". Hook omitido.')
        return
    _fix_company_access(env, website)
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
    _fix_company_access(env, website)
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

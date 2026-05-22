import base64
import os

from odoo import api, SUPERUSER_ID

_IMG_DIR = os.path.join(os.path.dirname(__file__), 'static', 'src', 'img', 'categories')

TROFEOS_CATEGORIES = [
    # (name, sequence, img_file, [(child_name, child_seq), ...])
    ('Trofeos', 10, 'trofeos.svg', [
        ('Trofeos Resina', 1),
        ('Trofeos Metal', 2),
        ('Trofeos Acrílico', 3),
        ('Trofeos Personalizados', 4),
    ]),
    ('Medallas', 20, 'medallas.svg', [
        ('Medallas Zinc', 1),
        ('Medallas Acrílico', 2),
        ('Medallas Deportivas', 3),
        ('Medallas Corporativas', 4),
    ]),
    ('Placas', 30, 'placas.svg', [
        ('Placas Aluminio', 1),
        ('Placas Madera', 2),
        ('Placas Acrílico', 3),
    ]),
    ('Grabado Láser', 40, 'grabado.svg', []),
    ('Corporativo', 50, 'corporativo.svg', []),
]


def _load_image(filename):
    path = os.path.join(_IMG_DIR, filename)
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return None


def _ensure_categories(env, website):
    Cat = env['product.public.category']
    existing = Cat.search([('parent_id', '=', False), ('website_id', '=', website.id)], limit=1)
    if existing:
        return
    for parent_name, seq, img_file, children in TROFEOS_CATEGORIES:
        img_b64 = _load_image(img_file)
        parent = Cat.search([
            ('name', '=', parent_name),
            ('parent_id', '=', False),
            ('website_id', '=', website.id),
        ], limit=1)
        vals = {'sequence': seq}
        if img_b64:
            vals['image_1920'] = img_b64
        if not parent:
            vals.update({'name': parent_name, 'website_id': website.id})
            parent = Cat.create(vals)
        else:
            parent.write(vals)
        for child_name, child_seq in children:
            child = Cat.search([
                ('name', '=', child_name),
                ('parent_id', '=', parent.id),
                ('website_id', '=', website.id),
            ], limit=1)
            if not child:
                Cat.create({
                    'name': child_name,
                    'sequence': child_seq,
                    'parent_id': parent.id,
                    'website_id': website.id,
                })
            else:
                child.write({'sequence': child_seq})


def _ensure_menus(env, website):
    Menu = env['website.menu']
    Cat = env['product.public.category']
    top_menu = website.menu_id
    if not top_menu:
        return
    # Avoid re-creating if already done
    if Menu.search([('website_id', '=', website.id), ('url', '=', '/trofeos')], limit=1):
        return

    for label, url, seq in [
        ('Inicio', '/trofeos', 5),
        ('Colección', '/shop', 10),
        ('Servicios', '/servicios-trofeos', 20),
        ('Empresas', '/empresas-trofeos', 30),
        ('Nosotros', '/quienes-somos-trofeos', 40),
    ]:
        if not Menu.search([('website_id', '=', website.id), ('url', '=', url)], limit=1):
            Menu.create({
                'name': label,
                'url': url,
                'parent_id': top_menu.id,
                'website_id': website.id,
                'sequence': seq,
            })

    cats = Cat.search([('parent_id', '=', False), ('website_id', '=', website.id)],
                      order='sequence asc')
    for idx, cat in enumerate(cats):
        cat_url = '/coleccion-trofeos/%s' % cat.id
        parent_menu = Menu.search([('website_id', '=', website.id), ('url', '=', cat_url)], limit=1)
        if not parent_menu:
            parent_menu = Menu.create({
                'name': cat.name,
                'url': cat_url,
                'parent_id': top_menu.id,
                'website_id': website.id,
                'sequence': 50 + idx,
            })
        children = Cat.search([('parent_id', '=', cat.id), ('website_id', '=', website.id)],
                               order='sequence asc')
        for child in children:
            child_url = '/shop?category=%s' % child.id
            if not Menu.search([
                ('website_id', '=', website.id),
                ('parent_id', '=', parent_menu.id),
                ('url', '=', child_url),
            ], limit=1):
                Menu.create({
                    'name': child.name,
                    'url': child_url,
                    'parent_id': parent_menu.id,
                    'website_id': website.id,
                    'sequence': child.sequence,
                })

    if not Menu.search([('website_id', '=', website.id), ('url', '=', '/contacto-trofeos')], limit=1):
        Menu.create({
            'name': 'Contacto',
            'url': '/contacto-trofeos',
            'parent_id': top_menu.id,
            'website_id': website.id,
            'sequence': 99,
        })


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    if not website:
        return
    lang = (
        env['res.lang'].search([('code', '=', 'es_CL')], limit=1)
        or env['res.lang'].search([('code', '=', 'es')], limit=1)
    )
    vals = {'homepage_url': '/trofeos'}
    if lang:
        vals['language_ids'] = [(6, 0, [lang.id])]
        vals['default_lang_id'] = lang.id
    website.write(vals)
    _ensure_categories(env, website)
    _ensure_menus(env, website)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env['website'].search([('name', '=', 'Trofeos')], limit=1)
    if website:
        env['product.public.category'].search([('website_id', '=', website.id)]).unlink()

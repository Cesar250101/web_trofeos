# -*- coding: utf-8 -*-
"""Sincroniza public_categ_ids de los productos desde WooCommerce (REST API).

Descarga las categorías y productos de la tienda WooCommerce de Trofeos, mapea
cada categoría a su product.public.category y asigna public_categ_ids a los
productos de Odoo emparejando por SKU (default_code). Los productos WC de tipo
"variable" se resuelven leyendo los SKU de sus variaciones.

Esta misma lógica se ejecuta automáticamente al actualizar el módulo
(`-u web_trofeos`, vía post_update_hook). Este script sirve para lanzarla a mano.

Uso (desde c:\\Program Files\\Odoo 16\\server):

    .\\.venv\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d clicksale --no-http ^
        < addons\\web_trofeos\\scripts\\sync_woo_categories.py

(en bash / una sola línea):

    ./.venv/Scripts/python.exe odoo-bin shell -c odoo.conf -d clicksale --no-http \
        < addons/web_trofeos/scripts/sync_woo_categories.py
"""

from odoo.addons.web_trofeos import hooks

website = env['website'].search([('name', '=', 'Trofeos')], limit=1)  # noqa: F821 (env inyectado por odoo shell)
if not website:
    print('ERROR: no existe el sitio web "Trofeos" en esta base de datos.')
else:
    print('Iniciando sync WooCommerce → public_categ_ids para el sitio "Trofeos"...')
    hooks._sync_woo_public_categs(env, website)  # noqa: F821
    env.cr.commit()  # noqa: F821
    print('Sync completado y confirmado (commit).')

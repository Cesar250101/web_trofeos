# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module overview

`web_trofeos` is an Odoo 16 website module for a trophies, medals, and engraving shop (B2B + B2C). It overrides `website` layout and `website_sale` visuals, provides 16 custom snippets, and syncs product categories from a WooCommerce store.

**Dependencies:** `website`, `website_sale`

## Common commands

```powershell
# Install or upgrade the module
python odoo-bin -c odoo.conf -u web_trofeos --stop-after-init

# Upgrade (triggers post_update_hook → re-sync WC categories + menus)
python odoo-bin -c odoo.conf -u web_trofeos --stop-after-init

# Start Odoo server
python odoo-bin -c odoo.conf
```

All commands run from `c:\Program Files\Odoo 16\server`.

## Architecture

### Layout scoping — the `.tr-body` guard

All frontend CSS is scoped under `.tr-body`, which is injected via `tr_body_class` template only when `website.name == 'Trofeos'`. This prevents styles from bleeding into other websites on the same Odoo instance. The header and footer overrides use the same `website.name == 'Trofeos'` guard in XPath templates.

### SCSS layer order (load order matters)

1. `primary_variables.scss` — Bootstrap variable overrides, loaded with `prepend` so it runs before Odoo core SCSS
2. `tr_tokens.scss` — CSS custom properties (`--tr-*`) for the entire design system
3. `tr_section_common.scss` — Shared utility classes (`.tr-grid`, `.tr-card`, `.tr-btn`, `.tr-input`, `.tr-section-*`, `.tr-eyebrow`)
4. Per-snippet SCSS files — each snippet has its own file

Always use `--tr-*` CSS variables in snippets, not hardcoded values. The token file is the single source of truth for colors, spacing, typography, and motion.

### Snippet pattern

Every snippet follows this consistent structure:
- **XML** in `views/snippets/s_tr_<name>.xml` — QWeb template with `id="s_tr_<name>"`
- **SCSS** in `static/src/scss/snippets/s_tr_<name>.scss` — scoped under `.s_tr_<name>`
- **JS** in `static/src/js/snippets/s_tr_<name>/000.js` (only for interactive snippets)
- **Thumbnail** in `static/src/img/snippets/thumb_<name>.svg`
- Registration in `views/snippets/snippets.xml` (the `snippets_trofeos` template injected before `#snippet_content`)

JS snippets use `/** @odoo-module **/` and export a vanilla object `{ selector, start(el) }`, initialized via `DOMContentLoaded`. They do **not** use Odoo's `publicWidget` registry — just direct DOM queries.

### Routes

All routes use the `-trofeos` suffix to avoid collisions with other websites on the instance:

| Route | Controller method | Template |
|---|---|---|
| `/trofeos` | `home` | `web_trofeos.tr_home` |
| `/quienes-somos-trofeos` | `quienes_somos` | `web_trofeos.tr_quienes_somos_page` |
| `/servicios-trofeos` | `servicios` | `web_trofeos.tr_servicios_page` |
| `/empresas-trofeos` | `empresas` | `web_trofeos.tr_empresas_page` |
| `/contacto-trofeos` | `contacto` | `web_trofeos.tr_contacto_page` |
| `/coleccion-trofeos/<category>` | `category_page` | `web_trofeos.tr_category_page` |

The `/contacto-trofeos` route accepts `?tipo=` and `?cantidad=` query params (pre-fills the quote form from the calculator).

### WooCommerce category sync

`hooks.py` syncs `product.public.category` from a WooCommerce store on install and every `--update`. The sync:
1. Reads WC credentials from `res.company` (fields `woo_url`, `woo_consumer_key`, `woo_consumer_secret`, `woo_version`) → falls back to `ir.config_parameter` keys `web_trofeos.wc_url / wc_key / wc_secret / wc_version`
2. Tries WC REST API (`/wp-json/wc/v2/products/categories`, paginated)
3. Falls back to HTML scraping of `/shop/` and `/product-category/` pages if the API fails
4. Deletes all existing categories for the Trofeos website, then recreates parents first, children second
5. Generates a glassmorphic SVG image per category (`_get_premium_svg`) keyed on the category name

`models/website.py` exposes `action_sync_wp_categories()` on the `website` model to trigger the sync manually (also called from `data/sync_categories.xml` on every update).

### Header navigation

`tr_header.xml` builds the nav dynamically: it queries `product.public.category` and separates categories into a fixed "Productos" mega-dropdown (Copas, Trofeos, Medallas, Maderas, Cristales, Sublimación, IMPRESIÓN DIRECTA COLOR, Insumos) and remaining top-level categories (Licenciaturas, Fiestas Patrias, Deportes). A hidden `<ul id="top_menu" class="d-none">` satisfies Odoo's native `auto_hide_menu.js`.

### Design tokens quick reference (Trofeos Premium — heraldic luxury)

- **Colors:** `--tr-black` (#0a0a0a), `--tr-onyx` (#141414), `--tr-graphite` (#1f1f1f), `--tr-bone` (#faf6ec), `--tr-platinum` (#c9c9c9)
- **Gold scale:** `--tr-gold-{50..800}` — core `#d4a437` (`--tr-gold-400`); use `--tr-grad-gold` for headlines, badges, CTAs
- **Fonts:** `--tr-font-display` (Anton — hero headlines), `--tr-font-heading` (Barlow Condensed — section titles, uppercase), `--tr-font-body` (Barlow — copy), `--tr-font-serif` (Cinzel — engraving feel, sparingly)
- **Spacing:** `--tr-space-{1..10}` (4–128px scale, 8pt rhythm); `--tr-gutter` 32px, `--tr-container` 1440px
- **Radii:** Modest curves — `6px` default, `8px` cards, `12px` panels, `999px` pills/badges
- **Shadows:** `--tr-sh-inset-gold` (inset rim on gold buttons), `--tr-sh-trophy`, `--tr-sh-gold-glow`
- **Patterns:**
  - Dark sections layer `radial-gradient(ellipse at 50% 0%, rgba(212,164,55,0.20) 0%, rgba(10,10,10,0) 60%)` over `--tr-onyx` for the stage-light glow
  - Product image areas use `linear-gradient(180deg, #1f1f1f, #0a0a0a)` + amber radial spotlight
  - Gold text is never flat — apply `background: var(--tr-grad-gold); -webkit-background-clip: text` for `.tr-gold-word`
- **Legacy aliases:** older `--tr-navy`/`--tr-ink`/`--tr-surface-*` tokens still resolve via remaps at the bottom of `tr_tokens.scss`, so unmodified snippets keep working

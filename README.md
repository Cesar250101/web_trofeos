# Web Trofeos Site

**Versión:** 16.0.1.0.0
**Licencia:** LGPL-3
**Autor:** Method
**Categoría:** Website

Módulo Odoo 16 para sitio web de trofeos, medallas y grabado, con soporte **B2B y B2C**. Incluye snippets reutilizables, layout personalizado con diseño heráldico premium, calculadora de cotización, sincronización de categorías desde WooCommerce y override visual de `website_sale`.

---

## Diseño Premium Heráldico

El módulo implementa un sistema de diseño de lujo heráldico con las siguientes características:

- **Paleta oscura:** negro profundo (`#0a0a0a`), ónix (`#141414`), grafito (`#1f1f1f`), hueso/marfil (`#faf6ec`)
- **Escala dorada de 9 pasos** (`--tr-gold-50` a `--tr-gold-800`) con gradiente metálico (`--tr-grad-gold`) aplicado a titulares, badges y CTAs
- **Tipografías:** Anton (display hero), Barlow Condensed (títulos uppercase), Barlow (cuerpo), Cinzel (acento heráldico)
- **Aislamiento CSS** mediante guarda `.tr-body` — los estilos solo aplican cuando `website.name == 'Trofeos'`, sin afectar otros sitios en la instancia

---

## Características

### Layout y diseño
- **Header oscuro** con banda superior (Despacho/Importadores/contacto), wordmark dorado y nav mega-dropdown de productos
- **Footer heráldico oscuro** con información de contacto y enlaces relevantes
- **Sistema de tokens CSS** (`tr_tokens.scss`) y variables Bootstrap (`primary_variables.scss`) — fuente única de verdad para colores, tipografías y espaciados
- **Override visual de `website_sale`** — tienda integrada con placas de imagen oscuras, precio en gradiente dorado y filtros tipo pill

### Páginas incluidas

| Página | URL |
|---|---|
| Inicio | `/trofeos` |
| Quiénes somos | `/quienes-somos-trofeos` |
| Servicios | `/servicios-trofeos` |
| Empresas (B2B) | `/empresas-trofeos` |
| Contacto / Cotización | `/contacto-trofeos` |
| Categoría de productos | `/coleccion-trofeos/<category>` |

La ruta `/contacto-trofeos` acepta los parámetros `?tipo=` y `?cantidad=` para pre-llenar el formulario desde la calculadora.

### Snippets para el editor de sitio web

#### Página de inicio
| Snippet | Descripción |
|---|---|
| `s_tr_hero` | Hero estático oscuro con titular Anton, anillos rotativos y trofeo SVG |
| `s_tr_trust_bar` | Banda USP oscura — Despacho 24-72h, Importadores, Grabado láser, Cotización 24h |
| `s_tr_featured_products` | Productos destacados con placas de imagen heráldicas |
| `s_tr_categories` | Grid 6 columnas con overlay dorado en hover |
| `s_tr_services` | Servicios en superficie hueso con tiles ónix |
| `s_tr_clients` | Logos de clientes en caps serif sobre fondo blanco |
| `s_tr_quote_calculator` | Calculadora de cotización — dos columnas, precio en gradiente dorado |
| `s_tr_promo_banner` | Banner oscuro con titular display dorado y badge |
| `s_tr_bestsellers` | Más vendidos con estilo heráldico en superficie hueso |
| `s_tr_newsletter` | Sección oscura ónix con radial ámbar |
| `s_tr_map` | Columna de info oscura + mapa a la derecha |
| `s_tr_whatsapp` | Botón flotante verde siempre visible con animación pulse |

#### Páginas internas
| Snippet | Descripción |
|---|---|
| `s_tr_about_hero` | Hero oscuro con strip de stats y números dorados |
| `s_tr_about_team` | Equipo en superficie hueso con placa de foto oscura |
| `s_tr_services_detail` | Bloques alternados dos columnas + strip de proceso numerado |
| `s_tr_b2b_hero` | Hero split oscuro para empresas |
| `s_tr_b2b_benefits` | Grid 6 tarjetas con franja dorada superior |

### JavaScript interactivo
- **Hero** (`s_tr_hero`) — animación de anillos rotativos + float del trofeo SVG
- **Productos destacados** (`s_tr_featured_products`) — efectos de hover en tarjetas
- **Calculadora de cotización** (`s_tr_quote_calculator`) — cálculo dinámico de precio según cantidad, producto y grabado
- **WhatsApp** (`s_tr_whatsapp`) — botón flotante con apertura de chat
- **Campo de fecha** (`tr_date_input.js`) — auto-formato dd/mm/aaaa: inserta barras al tipear y valida en blur

### Sincronización de categorías desde WooCommerce

Al instalar o actualizar el módulo se sincronizan automáticamente las categorías de `product.public.category` desde una tienda WooCommerce:

1. Lee las credenciales desde `res.company` (`woo_url`, `woo_consumer_key`, `woo_consumer_secret`) o desde `ir.config_parameter` como fallback
2. Consume la REST API de WC (`/wp-json/wc/v2/products/categories`, paginado)
3. Fallback a scraping HTML de `/shop/` si la API no está disponible
4. Recrea las categorías (padres primero, luego hijos) con imágenes SVG glassmórficas generadas automáticamente
5. También disponible manualmente desde `models/website.py` → `action_sync_wp_categories()`

### Hooks de instalación
- `post_init_hook` — configuración inicial del sitio web y sincronización de categorías al instalar
- `uninstall_hook` — limpieza de datos al desinstalar

---

## Dependencias

- `website`
- `website_sale`

---

## Instalación

1. Copiar la carpeta `web_trofeos` en el directorio de addons de Odoo.
2. Actualizar la lista de módulos desde **Ajustes → Aplicaciones**.
3. Buscar **Web Trofeos Site** e instalar.

```powershell
# Instalar o actualizar desde consola
python odoo-bin -c odoo.conf -u web_trofeos --stop-after-init
```

---

## Estructura del módulo

```
web_trofeos/
├── controllers/          # Rutas personalizadas (-trofeos suffix)
├── data/
│   ├── website_data.xml  # Configuración inicial del sitio
│   └── sync_categories.xml  # Trigger de sync WooCommerce en upgrade
├── models/
│   └── website.py        # Extiende res.website con action_sync_wp_categories()
├── security/             # ir.model.access.csv
├── static/src/
│   ├── img/              # Imágenes y SVGs del tema
│   ├── js/
│   │   ├── snippets/     # JS por snippet interactivo
│   │   └── tr_date_input.js  # Auto-formato dd/mm/aaaa
│   └── scss/
│       ├── primary_variables.scss  # Overrides Bootstrap (prepend)
│       ├── tr_tokens.scss          # CSS custom properties --tr-*
│       ├── tr_layout.scss          # Header, footer, layout base
│       ├── tr_section_common.scss  # Utilidades compartidas (.tr-btn, .tr-card, etc.)
│       ├── tr_contacto.scss        # Página de contacto/cotización
│       ├── tr_website_sale.scss    # Override tienda online
│       └── snippets/               # SCSS por snippet
└── views/
    ├── layout/           # tr_layout.xml, tr_header.xml, tr_footer.xml
    ├── pages/            # Páginas del sitio
    └── snippets/         # Templates QWeb de snippets
```

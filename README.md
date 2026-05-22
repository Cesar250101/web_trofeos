# Web Trofeos Site

**Versión:** 16.0.1.0.0
**Licencia:** LGPL-3
**Autor:** Method
**Categoría:** Website

Módulo Odoo 16 para sitio web de trofeos, medallas y grabado, con soporte **B2B y B2C**. Incluye snippets reutilizables, layout personalizado, calculadora de cotización y override visual de `website_sale`.

---

## Características

### Layout y diseño
- **Header personalizado** con menú de navegación dinámico adaptado al rubro
- **Footer personalizado** con información de contacto y enlaces relevantes
- **Sistema de tokens CSS** (`tr_tokens.scss`) y variables primarias (`primary_variables.scss`) para gestión centralizada de colores, tipografías y espaciados
- **Override visual de `website_sale`** para integrar la tienda online con la identidad gráfica del sitio

### Páginas incluidas
| Página | URL |
|---|---|
| Inicio | `/` |
| Quiénes somos | `/quienes-somos` |
| Servicios | `/servicios` |
| Empresas (B2B) | `/empresas` |
| Contacto | `/contacto` |
| Categoría de productos | `/categoria` |

### Snippets para el editor de sitio web

#### Página de inicio
| Snippet | Descripción |
|---|---|
| `s_tr_hero` | Hero principal con llamado a la acción |
| `s_tr_trust_bar` | Barra de confianza con sellos o iconos destacados |
| `s_tr_featured_products` | Productos destacados |
| `s_tr_services` | Servicios ofrecidos (trofeos, medallas, grabado, personalización) |
| `s_tr_clients` | Galería o logos de clientes |
| `s_tr_quote_calculator` | Calculadora de cotización interactiva |
| `s_tr_promo_banner` | Banner de promoción o campaña |
| `s_tr_bestsellers` | Productos más vendidos |
| `s_tr_newsletter` | Formulario de suscripción a newsletter |
| `s_tr_map` | Mapa de ubicación |
| `s_tr_whatsapp` | Botón flotante de contacto por WhatsApp |

#### Páginas internas
| Snippet | Descripción |
|---|---|
| `s_tr_about_hero` | Hero de la página "Quiénes somos" |
| `s_tr_about_team` | Sección del equipo |
| `s_tr_services_detail` | Detalle de servicios (grabado, personalización) |
| `s_tr_b2b_hero` | Hero de la sección empresas B2B |
| `s_tr_b2b_benefits` | Beneficios para clientes corporativos |

### JavaScript interactivo
- **Hero animado** (`s_tr_hero`) — efectos visuales de entrada
- **Calculadora de cotización** (`s_tr_quote_calculator`) — cálculo dinámico de precios según cantidad y producto
- **Botón WhatsApp** (`s_tr_whatsapp`) — comportamiento flotante y apertura de chat

### Hooks de instalación
- `post_init_hook` — configuración inicial del sitio web al instalar el módulo
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

---

## Estructura del módulo

```
web_trofeos/
├── controllers/          # Controladores web (rutas personalizadas)
├── data/                 # Datos iniciales del sitio web
├── security/             # Reglas de acceso (ir.model.access.csv)
├── static/src/
│   ├── img/              # Imágenes y SVGs del tema
│   ├── js/               # Scripts de snippets
│   └── scss/             # Estilos del tema y snippets
└── views/
    ├── layout/           # Header, footer y layout base
    ├── pages/            # Páginas del sitio
    └── snippets/         # Snippets reutilizables
```

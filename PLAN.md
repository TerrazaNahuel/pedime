# PediMe — Plan de Desarrollo

> Plataforma SaaS de menú / catálogo digital con pedidos por WhatsApp.
> Desarrollo por Nahuel Axel Terraza — 2026.

---

## FASE 1 — Fundación y Deuda Técnica ✅

| # | Feature | Estado |
|---|---------|--------|
| 1 | Secret key en variable de entorno (.env + python-dotenv) | ✅ |
| 2 | Protección CSRF (Double Submit Cookie) | ✅ |
| 3 | Validación de longitud y formato en inputs (register, products, settings) | ✅ |
| 4 | Sanitización XSS en dashboard (`tojson` en contextos JS) | ✅ |
| 5 | Manejo de errores + logging (404/500 handlers, logger jerárquico) | ✅ |
| 6 | `.gitignore` (pycache, .env, .venv, IDE, OS) | ✅ |
| 7 | Alembic migraciones configurado + migración inicial | ✅ |
| 8 | Rate limiter (login 5/min, register 3/5min) | ✅ |
| 9 | Password policy (8+ chars, mayúscula, minúscula, dígito) | ✅ |
| 10 | Session security (session.clear() en login/register, https_only) | ✅ |
| 11 | Security headers (X-Frame-Options, X-Content-Type-Options, HSTS, Referrer-Policy, CSP) | ✅ |
| 12 | Email redactado en logs | ✅ |
| 13 | Migración SQL Server → SQLite | ✅ |
| 14 | Modo solo lectura en horario cerrado | ✅ |
| 15 | Config deploy Railway (Procfile, runtime.txt, railway.json, render.yaml) | ✅ |
| 16 | SECRET_KEY con fallback automático si no está en .env | ✅ |
| 17 | Código muerto eliminado | ✅ |
| 18 | Deprecation warnings: Pydantic V2 ConfigDict, lifespan, utcnow | ✅ |
| 19 | Validación horario coherente (apertura/cierre) | ✅ |
| 20 | Soporte PostgreSQL (Railway) + SQLite (local) intercambiables | ✅ |
| 21 | Alembic migrations ejecutadas al startup | ✅ |
| 22 | Dominio dinámico en dashboard (base_url desde request) | ✅ |
| 23 | Precio con decimales en dashboard | ✅ |
| 24 | Eliminar elementos muertos del login (Recordarme, olvidé contraseña) | ✅ |
| 25 | CSRF cookie centralizada (COOKIE_CONFIG) | ✅ |
| 26 | N+1 query en reorder → bulk update | ✅ |
| 27 | Carrito persistente en localStorage | ✅ |

---

## FASE 2 — Experiencia de Usuario Pública ✅

| # | Feature | Estado |
|---|---------|--------|
| 28 | Diseño mobile-first responsive (Tailwind CSS) | ✅ |
| 29 | Modo oscuro nativo | ✅ |
| 30 | Loading spinner mientras carga el menú | ✅ |
| 31 | Toast de "agregado al carrito" | ✅ |
| 32 | Botón flotante de carrito con contador | ✅ |
| 33 | Drawer lateral para el carrito | ✅ |
| 34 | Selector de entrega (domicilio / retiro) con campos condicionales | ✅ |
| 35 | Selector de método de pago (transferencia / efectivo) | ✅ |
| 36 | Comentario del pedido (textarea) | ✅ |
| 37 | Fotos de productos en el menú | ✅ |
| 38 | Búsqueda/filtro de productos en tiempo real | ✅ |
| 39 | Navegación rápida por categorías (scroll horizontal) | ✅ |
| 40 | Personalización de colores/marca por comercio | ✅ |
| 41 | Menú colapsable por categorías | ✅ |

---

## FASE 3 — Administración Avanzada ✅

| # | Feature | Estado |
|---|---------|--------|
| 42 | Dashboard con tabs persistentes (HTMX) sin recarga de página | ✅ |
| 43 | CRUD de productos (crear, editar, eliminar, ocultar) | ✅ |
| 44 | CRUD de categorías (crear, editar inline, eliminar) | ✅ |
| 45 | Configuración del comercio (nombre, email, WhatsApp, password) | ✅ |
| 46 | Toggle de disponibilidad de producto (mostrar/ocultar) | ✅ |
| 47 | Configuración de delivery (precio, disponible) | ✅ |
| 48 | Configuración de métodos de pago (transferencia, efectivo) | ✅ |
| 49 | Ordenar productos por drag & drop (SortableJS) | ✅ |
| 50 | Duplicar producto | ✅ |
| 51 | Importar/exportar productos (CSV) | ✅ |
| 52 | Previsualización del menú público desde admin | ✅ |
| 53 | Estadísticas del menú (vistas, clics en WhatsApp, conversión) | ✅ |
| 54 | Plan gratis / plan premium (upgrade UI, expiración automática) | ✅ |
| 55 | Super admin (gestionar stores, planes, reset pass, eliminar) | ✅ |

---

## FASE 4 — Testing y Calidad ✅

| # | Feature | Estado |
|---|---------|--------|
| 56 | Tests de menú público (6 tests) | ✅ |
| 57 | Tests de seguridad (19 tests: XSS, SQLi, CSRF, rate limit, headers) | ✅ |
| 58 | Tests de admin CRUD (19 tests: productos, categorías, settings) | ✅ |
| 59 | Tests de super admin (12 tests) | ✅ |
| 60 | Linting con Ruff (target py312, line-length 120) | ✅ |
| 61 | Fix: Modal duplicado en HTMX swap | ✅ |
| 62 | Fix: Unificar create/edit producto en un solo endpoint | ✅ |

---

## FASE 5 — Landing y Branding ✅

| # | Feature | Estado |
|---|---------|--------|
| 63 | Landing page con hero, pasos, público objetivo | ✅ |
| 64 | 6 cards "¿Para quién es?" (restaurantes, bebidas, ropa, limpieza, regalos, almacén) | ✅ |
| 65 | Logo en círculo 160×160 con object-contain | ✅ |
| 66 | Favicon personalizado | ✅ |
| 67 | README.md con setup, tests, estructura y deploy | ✅ |
| 68 | Código 100% comentado en español (docstrings + inline) | ✅ |

---

## FASE 6 — Personalización de Productos (Variantes) ✅

| # | Feature | Estado |
|---|---------|--------|
| 69 | Migración DB: columna `variants` en products (JSON) | ✅ |
| 70 | Modelo: campo `variants` en Product | ✅ |
| 71 | Schema: `variants` en ProductOut (API pública) | ✅ |
| 72 | Admin API: crear/editar producto con variantes | ✅ |
| 73 | Admin API: validación de variantes (JSON, nombres, precios, límites) | ✅ |
| 74 | Admin API: plan Premium requerido para variantes | ✅ |
| 75 | Admin UI: modal con editor de variantes (agregar/quitar filas) | ✅ |
| 76 | Menú público: selector de variante por producto (select/radio) | ✅ |
| 77 | Carrito: mostrar variante seleccionada en nombre y precio | ✅ |
| 78 | WhatsApp: incluir variante en el mensaje | ✅ |
| 79 | CSV export/import con columna variants | ✅ |
| 80 | Tests: crear, editar, validar variantes en API | ✅ |

---

## FASE 7 — Pagos y Facturación 🔨

| # | Feature | Estado |
|---|---------|--------|
| 81 | Integración con Mercado Pago (preferencias + webhook async + fix body parse) | ✅ |
| 82 | QR para transferencia bancaria (CBU/alias) | ⏳ |
| 83 | Factura electrónica / comprobante simple | ⏳ |
| 84 | Cobro con tarjeta (Mercado Pago Checkout API) | ✅ |

---

## FASE 8 — Notificaciones y Comunicación ⏳

| # | Feature | Estado |
|---|---------|--------|
| 85 | Mensaje formateado a WhatsApp con resumen del pedido | ✅ |
| 86 | Notificación al cliente cuando el pedido está listo | ⏳ |
| 87 | Email de confirmación al cliente | ⏳ |
| 88 | WhatsApp Business API (en vez de wa.me) | ⏳ |
| 89 | Recordatorio automático de pedido pendiente | ⏳ |

---

## FASE 9 — Multi-Tenant y Escalabilidad ⏳

| # | Feature | Estado |
|---|---------|--------|
| 90 | Registro de nuevo comercio (signup) | ✅ |
| 91 | Login con sesión | ✅ |
| 92 | Slug único por comercio (URL amigable) | ✅ |
| 93 | Seed data inicial (comercio demo) | ✅ |
| 94 | Soporte PostgreSQL (Railway) + SQLite (local) | ✅ |
| 95 | Subdominio personalizado (micomida.pedime.app) | ⏳ |
| 96 | Dominio personalizado (menu.micomida.com) | ⏳ |
| 97 | Múltiples usuarios por comercio (roles) | ❌ eliminado |

---

## FASE 10 — Infraestructura y DevOps ⏳

| # | Feature | Estado |
|---|---------|--------|
| 98 | Alembic para migraciones (ejecutadas al startup) | ✅ |
| 99 | Logging estructurado (fecha, nivel, módulo) | ✅ |
| 100 | Secret key desde variable de entorno | ✅ |
| 101 | Docker / docker-compose para despliegue | ⏳ |
| 102 | CI/CD (GitHub Actions) | ⏳ |
| 103 | HTTPS (certbot / Caddy) | ⏳ |
| 104 | Backup automático de base de datos | ⏳ |

---

**Leyenda:** ✅ Completado | ⏳ Pendiente | 🔨 En progreso | ❌ Eliminado

---

## FASE 11 — Refactor y Deuda Técnica (Ronda 3) ✅

| # | Feature | Estado |
|---|---------|--------|
| 105 | Webhook MP: eliminar imports muertos (hashlib/hmac), handler async con await request.json() | ✅ |
| 106 | Eliminar settings no usados: MP_PUBLIC_KEY, LOGOUT_MAX_ATTEMPTS, LOGOUT_WINDOW_SECONDS | ✅ |
| 107 | Mover imports lazy a tope de módulo (admin.py, admin_base.py, password.py) | ✅ |
| 108 | Reemplazar 13 onclick inline por data-action + event delegation en dashboard.js | ✅ |
| 109 | Fix bare catch sin logging en cart.js (console.warn) | ✅ |
| 110 | Extraer clases CSS duplicadas: form-input, stat-card, stat-value, stat-label, checkbox-custom | ✅ |
| 111 | Dividir renderMenu() 220 líneas → renderStoreDetails, renderClosedBanner, renderProductCard, renderCategorySection | ✅ |
| 112 | Dividir renderCartItems() 82 líneas → renderCartItemRow, updateWhatsAppButton | ✅ |
| 113 | Dividir renderDeliveryToggle() 80 líneas → renderDeliveryButtons, renderDeliveryFields | ✅ |
| 114 | Refactor update_settings con helpers: _validate_basic_fields, _validate_settings_visuals, _handle_password_change | ✅ |
| 115 | Health endpoint migrado de SessionLocal() a Depends(get_db) | ✅ |
| 116 | Código 100% comentado en español (backend Python, frontend JS, templates HTML) | ✅ |
| 117 | CSP: eliminado script inline de dashboard.html + todos los onclick → más cerca de quitar unsafe-inline | ✅ |
| 118 | 62 tests pasando después de todos los refactors | ✅ |

---

**Resumen:** 94 completadas · 12 pendientes · 1 eliminada

Última actualización: 13/07/2026

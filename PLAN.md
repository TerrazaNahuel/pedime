# PediMé — Plan de Desarrollo

> MVP de menú digital con pedidos por WhatsApp

---

## 🔴 FASE 1 — Corregir Deuda Técnica

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
| 11 | Security headers (X-Frame-Options, X-Content-Type-Options) | ✅ |
| 12 | Email redactado en logs | ✅ |
| 13 | Migración SQL Server → SQLite | ✅ |
| 14 | Modo solo lectura en horario cerrado | ✅ |
| 15 | Config deploy Railway (Procfile, runtime.txt, railway.json, requirements.txt raíz) | ✅ |
| 16 | SECRET_KEY con fallback automático si no está en .env | ✅ |
| 17 | Código muerto eliminado en auth.py (líneas post-return) | ✅ |
| 18 | Deprecation warnings: Pydantic V2 ConfigDict, lifespan, TemplateResponse, utcnow | ✅ |
| 19 | Validación horario coherente (apertura/cierre) en settings | ✅ |
| 20 | Soporte PostgreSQL via DATABASE_URL (Railway) con fallback a SQLite local | ✅ |
| 21 | Alembic migrations ejecutadas al startup (reemplaza create_all()) | ✅ |
| 22 | Dominio dinámico en dashboard (base_url desde request) | ✅ |
| 23 | Precio con decimales en dashboard (%.0f → %.2f) | ✅ |
| 24 | Eliminar checkbox 'Recordarme' sin implementación | ✅ |
| 25 | Eliminar link muerto '¿Olvidaste tu contraseña?' | ✅ |
| 26 | Renombrar imágenes con espacios (logo X.jpeg → logo-X.jpeg) | ✅ |
| 27 | CSRF cookie: centralizar COOKIE_CONFIG en csrf.py y reusar | ✅ |
| 28 | N+1 query en reorder → bulk update (1 query vs N queries) | ✅ |
| 29 | Carrito persistente en localStorage (no se pierde al refrescar) | ✅ |
| 30 | Security headers: Strict-Transport-Security, Referrer-Policy | ✅ |

## 🟢 FASE 3 — Experiencia de Usuario

| # | Feature | Estado |
|---|---------|--------|
| 31 | Diseño mobile-first responsive (Tailwind CSS) | ✅ |
| 32 | Modo oscuro nativo | ✅ |
| 33 | Loading spinner mientras carga el menú | ✅ |
| 34 | Toast de "agregado al carrito" | ✅ |
| 35 | Carrito persistente en sesión (en memoria + localStorage) | ✅ |
| 36 | Botón flotante de carrito con contador | ✅ |
| 37 | Drawer lateral para el carrito | ✅ |
| 38 | Selector de entrega (domicilio / retiro) con campos condicionales | ✅ |
| 39 | Selector de método de pago | ✅ |
| 40 | Comentario del pedido (textarea) | ✅ |
| 41 | Fotos de productos en el menú | ✅ |
| 42 | Búsqueda/filtro de productos en el menú | ✅ |
| 43 | Navegación rápida por categorías (scroll horizontal) | ✅ |
| 44 | Personalización de colores/marca por comercio | ✅ |
| 45 | Modo de sólo lectura para horario cerrado | ✅ |

## 🔵 FASE 4 — Administración Avanzada

| # | Feature | Estado |
|---|---------|--------|
| 46 | CRUD de productos (crear, editar, eliminar, ocultar) | ✅ |
| 47 | CRUD de categorías (crear, editar, eliminar) | ✅ |
| 48 | Configuración del comercio (nombre, email, WhatsApp, password) | ✅ |
| 49 | Toggle de disponibilidad de producto (mostrar/ocultar) | ✅ |
| 50 | Configuración de delivery (precio, disponible) | ✅ |
| 51 | Configuración de métodos de pago (transferencia, efectivo) | ✅ |
| 52 | Ordenar productos por arrastrar (drag & drop) | ✅ |
| 53 | Duplicar producto | ✅ |
| 54 | Importar/exportar productos (CSV) | ✅ |
| 55 | Previsualización del menú público desde admin | ✅ |
| 56 | Estadísticas del menú (vistas, clics en WhatsApp) | ⏳ |
| 57 | Múltiples usuarios por comercio (roles) | ⏳ |

## 🟣 FASE 5 — Pagos y Facturación

| # | Feature | Estado |
|---|---------|--------|
| 58 | Integración con Mercado Pago (link de pago) | ⏳ |
| 59 | QR para transferencia bancaria (CBU/alias) | ⏳ |
| 60 | Factura electrónica / comprobante simple | ⏳ |
| 61 | Cobro con tarjeta (Mercado Pago Checkout API) | ⏳ |

## 🟠 FASE 6 — Notificaciones y Comunicación

| # | Feature | Estado |
|---|---------|--------|
| 62 | Mensaje formateado a WhatsApp con resumen del pedido | ✅ |
| 63 | Incluir # de orden en el mensaje de WhatsApp | ❌ eliminado |
| 64 | Notificación al cliente cuando el pedido está listo | ⏳ |
| 65 | Email de confirmación al cliente | ⏳ |
| 66 | WhatsApp Business API (en vez de wa.me) | ⏳ |
| 67 | Recordatorio automático de pedido pendiente | ⏳ |

## ⚪ FASE 7 — Multi-Tenant y Escalabilidad

| # | Feature | Estado |
|---|---------|--------|
| 68 | Registro de nuevo comercio (signup) | ✅ |
| 69 | Login con sesión | ✅ |
| 70 | Slug único por comercio (URL amigable) | ✅ |
| 71 | Seed data inicial (comercio demo + categorías + productos) | ✅ |
| 72 | Soporte PostgreSQL (Railway) + SQLite (local) intercambiables | ✅ |
| 73 | Plan gratis / plan premium por comercio | ⏳ |
| 74 | Subdominio personalizado (micomida.pedime.app) | ⏳ |
| 75 | Dominio personalizado (menu.micomida.com) | ⏳ |

## 🟤 FASE 8 — Infraestructura y DevOps

| # | Feature | Estado |
|---|---------|--------|
| 76 | Alembic para migraciones de base de datos (ejecutadas al startup) | ✅ |
| 77 | Logging estructurado (fecha, nivel, módulo) | ✅ |
| 78 | Secret key desde variable de entorno | ✅ |
| 79 | Docker / docker-compose para despliegue | ⏳ |
| 80 | CI/CD (GitHub Actions) | ⏳ |
| 81 | Tests automatizados (44 tests: 25 seguridad + 19 admin CRUD) | ✅ |
| 82 | HTTPS (certbot / Caddy) | ⏳ |
| 83 | Backup automático de base de datos | ⏳ |

## 🧪 FASE 9 — Testing

| # | Feature | Estado |
|---|---------|--------|
| 84 | Tests de menú público (6 tests: rutas, API, login/register page) | ✅ |
| 85 | Tests de seguridad (19 tests: XSS, SQLi, CSRF, rate limit, headers) | ✅ |
| 86 | Tests de admin CRUD (19 tests: productos, categorías, settings) | ✅ |

## 📄 FASE 10 — Documentación y Código

| # | Feature | Estado |
|---|---------|--------|
| 87 | README.md con setup, tests, estructura y deploy | ✅ |
| 88 | Código comentado por bloques lógicos en español | ✅ |

---

**Leyenda:** ✅ Completado | ⏳ Pendiente | ❌ Eliminado

## 🎨 FASE 11 — Logo y Branding

| # | Feature | Estado |
|---|---------|--------|
| 89 | Landing page rebrand: "menú digital" → "catálogo digital", "Crear mi menú" → "Crear mi tienda", "Cargá tu menú" → "Cargá tus productos" | ✅ |
| 90 | 6 cards "¿Para quién es?" variadas | ✅ |
| 91 | Logo original restaurado (1076×718), display círculo 160×160 con `object-contain` | ✅ |
| 92 | Logo posicionado `-left-8` + `z-50` para visibilidad en mobile | ✅ |
| 93 | Favicon (logo-6.png como favicon.ico) en pestaña del navegador | ✅ |

## 🐛 FASE 12 — Bugfixes

| # | Feature | Estado |
|---|---------|--------|
| 94 | Cuentas duplicadas con mismo email — IntegrityError distingue email vs slug | ✅ |
| 95 | Stock opcional en producto (0 = sin límite) — modelo, migración, form, API, CSV | ✅ |
| 96 | Duplicado copia `sort_order` para aparecer justo debajo del original | ✅ |
| 97 | Límite 10 productos por categoría en duplicar e importar CSV | ✅ |

---

**Leyenda:** ✅ Completado | ⏳ Pendiente | ❌ Eliminado

Última actualización: 25/06/2026

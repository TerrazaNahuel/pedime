# PediMe — Menú Digital con Pedidos por WhatsApp

MVP de menú digital para restaurantes, pizzerías, hamburgueserías y cualquier comercio gastronómico. Creá tu menú online, compartí el link y recibí pedidos directo por WhatsApp.

## Stack Tecnológico

| Componente | Tecnología |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | HTML + Tailwind CSS + JavaScript vanilla |
| Base de datos | SQLite (SQLAlchemy ORM) |
| Templates | Jinja2 |
| Migraciones | Alembic |
| Testing | pytest + httpx + TestClient |
| Deploy | Railway / Heroku (Procfile) |

## Setup Local

```bash
# Clonar el repo
git clone <repo-url>
cd pedime

# Crear entorno virtual e instalar dependencias
cd backend
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt

# Configurar secret key (opcional — si no se setea, se genera una automática)
echo SECRET_KEY=tu_clave_secreta_aqui > .env

# Iniciar servidor
uvicorn main:app --reload --port 8000
```

Abrir [http://localhost:8000](http://localhost:8000).

## Seed Data

Al primer inicio se crea automáticamente un comercio demo:
- **Nombre:** SinCulpa.ar
- **Email:** sinculpa@pedime.app
- **Slug:** sinculpa
- **URL:** [http://localhost:8000/menu/sinculpa](http://localhost:8000/menu/sinculpa)
- **Contraseña:** se genera aleatoriamente y se loguea en la consola al iniciar el servidor.

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

### 44 tests distribuidos en 3 archivos:

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| `tests/test_menu.py` | 6 | Rutas públicas del menú, API JSON, páginas de login/register |
| `tests/test_security.py` | 19 | Password policy, CSRF, rate limiting, SQLi, XSS, validaciones, headers de seguridad |
| `tests/test_admin.py` | 19 | CRUD productos/categorías/settings, import/export CSV, logout |

## Estructura del Proyecto

```
pedime/
├── backend/
│   ├── main.py              # Punto de entrada FastAPI
│   ├── database.py          # Configuración SQLAlchemy
│   ├── models.py            # Modelos: Store, Category, Product
│   ├── schemas.py           # Schemas Pydantic para la API
│   ├── csrf.py              # Protección CSRF (Double Submit Cookie)
│   ├── ratelimit.py         # Rate limiter en memoria
│   ├── seed.py              # Seed data inicial
│   ├── routers/
│   │   ├── auth.py          # Login y registro
│   │   ├── admin.py         # Dashboard y sub-routers
│   │   ├── admin_base.py    # Dependencias compartidas del admin
│   │   ├── admin_products.py # CRUD de productos
│   │   ├── admin_categories.py # CRUD de categorías
│   │   ├── admin_settings.py # Configuración del comercio
│   │   └── menu_public.py   # Rutas públicas del menú
│   ├── templates/           # Templates Jinja2 del admin
│   ├── tests/               # Tests pytest
│   └── alembic/             # Migraciones de base de datos
├── frontend/
│   ├── menu.html            # Página HTML del menú público
│   └── js/cart.js           # Lógica del carrito en frontend
├── Procfile                 # Config de deploy (Railway/Heroku)
└── runtime.txt              # Versión de Python para deploy
```

## Features

### Público
- Menú responsive con Tailwind CSS (modo oscuro)
- Fotos de productos
- Búsqueda en tiempo real
- Navegación por categorías (scroll horizontal)
- Carrito de compras con cantidades
- Selector de entrega (domicilio / retiro)
- Selector de método de pago
- Comentario del pedido
- Envío del pedido por WhatsApp
- Modo solo lectura cuando el local está cerrado
- Colores personalizados por comercio

### Admin
- Dashboard con tabs (Productos / Categorías / Configuración)
- CRUD de productos (crear, editar, eliminar, ocultar)
- CRUD de categorías (crear, editar, eliminar)
- Drag & drop para ordenar productos
- Duplicar producto
- Importar/exportar productos (CSV)
- Configuración del comercio (nombre, email, WhatsApp, password)
- Configuración de delivery y métodos de pago
- Horarios de apertura/cierre
- Personalización visual (color primario, logo)

### Seguridad
- Protección CSRF (Double Submit Cookie)
- Rate limiting en login y register
- Password policy (8+ chars, mayúscula, minúscula, número)
- Session fixation prevention
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (Jinja2 autoescape + createElement)
- Validación de URLs (rechaza javascript:, data:)
- Headers de seguridad (X-Frame-Options, X-Content-Type-Options)
- Email redactado en logs

## Deploy en Railway

1. Subir el proyecto a GitHub
2. Crear proyecto en Railway → "Deploy from GitHub repo"
3. Agregar variable de entorno `SECRET_KEY` en Railway dashboard
4. La app se sirve automáticamente vía `Procfile`

---
Desarrollado por Nahuel Axel Terraza — 2026

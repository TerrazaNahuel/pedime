# PediMe — Menú Digital con Pedidos por WhatsApp

Plataforma SaaS de menú / catálogo digital. Creá tu tienda online, compartí el link y recibí pedidos directo por WhatsApp. Sin app store, sin comisiones.

## Stack

| Componente | Tecnología |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | HTML + Tailwind CSS + JavaScript vanilla |
| Admin | Jinja2 + HTMX + SortableJS |
| BD | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy 2.0 + Alembic |
| Tests | pytest + httpx (56 tests) |
| Deploy | Railway / Render |

## Setup Local

```bash
git clone <repo-url>
cd pedime/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
echo SECRET_KEY=clave_secreta > .env
uvicorn main:app --reload --port 8000
```

Abrir [http://localhost:8000](http://localhost:8000)

## Seed Data

Al primer inicio se crea un comercio demo:
- **Nombre:** ElAdmin · **Slug:** eladmin
- **Email:** nhlterraza@gmail.com · **Pass:** `Admin123!`
- **URL:** [http://localhost:8000/menu/eladmin](http://localhost:8000/menu/eladmin)

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Plan de Desarrollo

Ver [PLAN.md](PLAN.md) para el estado actual del proyecto, fases completadas y pendientes.

---

Desarrollado por Nahuel Axel Terraza — 2026

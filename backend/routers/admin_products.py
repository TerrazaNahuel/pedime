"""
CRUD de productos del panel de administración.

Operaciones: crear, editar, duplicar, eliminar, toggle visibilidad,
reordenar (drag & drop), exportar e importar CSV.
"""

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from database import get_db
from models import Category, Product
from decimal import Decimal
from routers.admin_base import get_authenticated_store, check_plan_limit, logger
from csrf import validate_csrf
import csv
import io
import re
import urllib.parse

router = APIRouter()

URL_PATTERN = re.compile(r"^https?://\S+$")


def validate_url(url: str) -> bool:
    """Valida que una URL sea HTTP(S) válida o esté vacía. Rechaza javascript:, data:, etc."""
    return not url or bool(URL_PATTERN.match(url))


@router.post("/admin/product")
def create_product(
    request: Request,
    name: str = Form(...), description: str = Form(""),
    price: Decimal = Form(...), category_id: int = Form(...),
    image_url: str = Form(""),
    available: str = Form("1"),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """Crea un nuevo producto. Valida longitud, precio, URL de imagen y límites del plan."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)
    limit_err = check_plan_limit(store, db)
    if limit_err:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(limit_err), status_code=302)
    if len(name) > 100:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El nombre del producto es demasiado largo"), status_code=302)
    if len(description) > 500:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("La descripción es demasiado larga"), status_code=302)
    if price < 0:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El precio no puede ser negativo"), status_code=302)
    if not validate_url(image_url):
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("La URL de la imagen no es válida"), status_code=302)
    if len(image_url) > 500:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("La URL de la imagen es demasiado larga"), status_code=302)
    if available not in ("0", "1"):
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Valor de disponibilidad inválido"), status_code=302)
    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Categoría no encontrada"), status_code=302)
    db.add(Product(name=name, description=description, price=price,
                   image_url=image_url, category_id=category_id, store_id=store.id,
                   available=(available == "1")))
    db.commit()
    logger.info("Producto creado store_id=%s category_id=%s", store.id, category_id)
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/product/{product_id}/edit")
def update_product(
    product_id: int, request: Request,
    name: str = Form(...), description: str = Form(""),
    price: Decimal = Form(...), category_id: int = Form(...),
    available: str = Form("0"),
    image_url: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """Edita un producto existente. Verifica que pertenezca al store autenticado."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)
    if len(name) > 100:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El nombre del producto es demasiado largo"), status_code=302)
    if len(description) > 500:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("La descripción es demasiado larga"), status_code=302)
    if price < 0:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El precio no puede ser negativo"), status_code=302)
    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Producto no encontrado"), status_code=302)
    if not validate_url(image_url):
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("La URL de la imagen no es válida"), status_code=302)
    if len(image_url) > 500:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("La URL de la imagen es demasiado larga"), status_code=302)
    if available not in ("0", "1"):
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Valor de disponibilidad inválido"), status_code=302)
    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Categoría no encontrada"), status_code=302)
    logger.info("Producto editado store_id=%s id=%s", store.id, product_id)
    prod.name = name
    prod.description = description
    prod.price = price
    prod.category_id = category_id
    prod.available = (available == "1")
    prod.image_url = image_url
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/product/{product_id}/duplicate")
def duplicate_product(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Duplica un producto agregando '(copia)' al nombre."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)
    limit_err = check_plan_limit(store, db)
    if limit_err:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(limit_err), status_code=302)
    original = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not original:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Producto no encontrado"), status_code=302)
    dup_name = original.name[:92] + " (copia)"
    dup = Product(
        name=dup_name,
        description=original.description,
        price=original.price,
        image_url=original.image_url,
        available=original.available,
        category_id=original.category_id,
        store_id=store.id,
    )
    db.add(dup)
    db.commit()
    logger.info("Producto duplicado store_id=%s from_id=%s new_id=%s", store.id, product_id, dup.id)
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/product/{product_id}/delete")
def delete_product(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Elimina un producto."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)
    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Producto no encontrado"), status_code=302)
    logger.info("Producto eliminado store_id=%s id=%s", store.id, product_id)
    db.delete(prod)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/product/{product_id}/toggle")
def toggle_product(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Alterna la visibilidad de un producto (available true/false)."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)
    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Producto no encontrado"), status_code=302)
    prod.available = not prod.available
    db.commit()
    logger.info("Producto toggle store_id=%s id=%s available=%s", store.id, product_id, prod.available)
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/products/reorder")
def reorder_products(request: Request, product_ids: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """
    Reordena los productos según una lista de IDs (drag & drop).
    El orden se recibe como string separado por comas desde SortableJS.
    """
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)
    try:
        ids = [int(x) for x in product_ids.split(",") if x.strip()]
    except ValueError:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("IDs de producto inválidos"), status_code=302)
    if len(ids) > 500:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Demasiados productos (máx 500)"), status_code=302)
    products_to_update = db.query(Product).filter(
        Product.id.in_(ids),
        Product.store_id == store.id,
    ).all()
    unique_ids = list(dict.fromkeys(ids))
    id_to_product = {p.id: p for p in products_to_update}
    for i, pid in enumerate(unique_ids):
        if pid in id_to_product:
            id_to_product[pid].sort_order = i
    db.commit()
    logger.info("Productos reordenados store_id=%s count=%s", store.id, len(ids))
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.get("/admin/products/export")
def export_products_csv(request: Request, db: Session = Depends(get_db)):
    """Exporta todos los productos del store como archivo CSV."""
    store = get_authenticated_store(request, db)
    products = db.query(Product).filter(Product.store_id == store.id).order_by(Product.sort_order, Product.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "description", "price", "category_id", "image_url", "available"])
    for p in products:
        writer.writerow([p.name, p.description or "", str(p.price), p.category_id, p.image_url or "", "1" if p.available else "0"])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=productos.csv"},
    )


@router.post("/admin/products/import")
def import_products_csv(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Importa productos desde un archivo CSV.
    Validaciones: extensión .csv, tamaño máx 10MB, codificación UTF-8.
    Retorna resumen con cantidad importada y hasta 5 errores.
    """
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    limit_err = check_plan_limit(store, db)
    if limit_err:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(limit_err), status_code=302)

    if file.filename is None or not file.filename.endswith(".csv"):
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El archivo debe ser CSV"), status_code=302)

    MAX_FILE_SIZE = 10 * 1024 * 1024
    raw = file.file.read(MAX_FILE_SIZE + 1)
    if len(raw) > MAX_FILE_SIZE:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El archivo es demasiado grande (máx 10 MB)"), status_code=302)

    content_type = file.content_type or ""
    if content_type not in ("text/csv", "text/plain", "application/octet-stream", ""):
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El archivo debe ser un CSV válido"), status_code=302)

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El archivo debe estar codificado en UTF-8"), status_code=302)
    reader = csv.DictReader(io.StringIO(content))

    created = 0
    errors = []
    for row_num, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        if not name:
            errors.append(f"Fila {row_num}: nombre requerido")
            continue
        if len(name) > 100:
            errors.append(f"Fila {row_num}: nombre demasiado largo")
            continue

        description = row.get("description", "").strip()[:500]
        image_url = row.get("image_url", "").strip()[:500]

        try:
            price = Decimal(row.get("price", "0"))
        except Exception:
            errors.append(f"Fila {row_num}: precio inválido")
            continue
        if price < 0:
            errors.append(f"Fila {row_num}: precio negativo")
            continue

        try:
            category_id = int(row.get("category_id", "0"))
        except (ValueError, TypeError):
            errors.append(f"Fila {row_num}: category_id inválido")
            continue

        cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
        if not cat:
            errors.append(f"Fila {row_num}: categoría {category_id} no encontrada")
            continue

        available = row.get("available", "1").strip() in ("1", "true", "yes")

        db.add(Product(
            name=name, description=description, price=price,
            image_url=image_url, category_id=category_id, store_id=store.id,
            available=available,
        ))
        created += 1

    db.commit()
    logger.info("Productos importados store_id=%s creados=%s errores=%s", store.id, created, len(errors))

    msg = f"Se importaron {created} productos."
    if errors:
        msg += " Errores: " + "; ".join(errors[:5])

    return RedirectResponse(url=f"/admin/dashboard?msg={urllib.parse.quote(msg)}", status_code=302)

"""V455: independent, store-scoped product list and compact editing surface."""
from __future__ import annotations

import json
import math
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from fastapi import Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

import nowup_subcategories448
from nowup_pairs256 import validate_pairs

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
CLOSED = ("cancelled", "rejected")
PERIODS = {"30": 30, "90": 90, "365": 365, "all": None}
PER_PAGE = 10


def _fold(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value or "")) if not unicodedata.combining(c)).casefold().strip()


def _ids(raw):
    return [int(x) for x in str(raw or "").split(",") if x.isdigit()]


def _sales(conn, store_id, period):
    """Only completed orders count as sales. Cancelled orders are separate."""
    days = PERIODS[period]
    cutoff = ((datetime.now(LOCAL_TZ) - timedelta(days=days)).date().isoformat() if days else "")
    totals = {}
    sources = [
        ("""SELECT oi.product_id AS id,
            SUM(CASE WHEN o.status='completed' THEN oi.quantity ELSE 0 END) sold,
            SUM(CASE WHEN o.status='completed' THEN oi.quantity*oi.unit_price_cents ELSE 0 END) revenue,
            SUM(CASE WHEN o.status IN ('cancelled','rejected') THEN oi.quantity ELSE 0 END) cancelled,
            COUNT(DISTINCT CASE WHEN o.status='completed' THEN substr(o.created_at,1,10) END) days
            FROM order_items oi JOIN orders o ON o.id=oi.order_id
            WHERE o.professional_id=? AND (?='' OR o.created_at>=?)
            AND oi.product_id IS NOT NULL GROUP BY oi.product_id""", (store_id, cutoff, cutoff)),
        ("""SELECT mi.product_id AS id,
            SUM(CASE WHEN ms.status='completed' THEN mi.quantity ELSE 0 END) sold,
            SUM(CASE WHEN ms.status='completed' THEN mi.quantity*mi.unit_price_cents ELSE 0 END) revenue,
            SUM(CASE WHEN ms.status='cancelled' THEN mi.quantity ELSE 0 END) cancelled,
            COUNT(DISTINCT CASE WHEN ms.status='completed' THEN substr(ms.created_at,1,10) END) days
            FROM manual_items107 mi JOIN manual_sales107 ms ON ms.id=mi.sale_id
            WHERE ms.professional_id=? AND (?='' OR ms.created_at>=?)
            AND mi.product_id IS NOT NULL GROUP BY mi.product_id""", (store_id, cutoff, cutoff)),
    ]
    # Each source has unique sales-day dates. Merge days via a separate UNION.
    try:
        query = """SELECT product_id,COUNT(DISTINCT day) days FROM (
        SELECT oi.product_id,substr(o.created_at,1,10) day FROM order_items oi
          JOIN orders o ON o.id=oi.order_id
          WHERE o.professional_id=? AND o.status='completed' AND (?='' OR o.created_at>=?)
        UNION ALL
        SELECT mi.product_id,substr(ms.created_at,1,10) day FROM manual_items107 mi
          JOIN manual_sales107 ms ON ms.id=mi.sale_id
          WHERE ms.professional_id=? AND ms.status='completed' AND (?='' OR ms.created_at>=?)
        ) sales_days GROUP BY product_id"""
        distinct_days = {int(r["product_id"]): int(r["days"]) for r in conn.execute(query, (store_id, cutoff, cutoff, store_id, cutoff, cutoff)).fetchall() if r["product_id"] is not None}
    except Exception:
        distinct_days = None
    for i, (sql, params) in enumerate(sources):
        try:
            rows = conn.execute(sql, params).fetchall()
        except Exception:
            if i == 0:
                raise
            continue  # An older store may not yet have a manual ledger.
        for r in rows:
            pid = int(r["id"])
            data = totals.setdefault(pid, {"sold": 0, "revenue": 0, "cancelled": 0, "days": 0})
            data["sold"] += int(r["sold"] or 0)
            data["revenue"] += int(r["revenue"] or 0)
            data["cancelled"] += int(r["cancelled"] or 0)
            if distinct_days is None:
                data["days"] += int(r["days"] or 0)
    if distinct_days is not None:
        for pid, count in distinct_days.items():
            totals.setdefault(pid, {"sold": 0, "revenue": 0, "cancelled": 0, "days": 0})["days"] = count
    return totals


def install(ns):
    app = ns["app"]
    db = ns["db"]
    require_user = ns["require_user"]
    require_premium_catalog = ns["require_premium_catalog"]
    templates = ns["templates"]
    context = ns["context"]
    save_image = ns["save_image"]
    price_to_cents = ns["price_to_cents"]
    now_iso = ns["now_iso"]

    @app.on_event("startup")
    def prepare_product_audit455():
        conn = db()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS product_audit455(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professional_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_product_audit455 ON product_audit455(professional_id,product_id,created_at)")
            conn.commit()
        finally:
            conn.close()

    def return_url(form, next_id=None, ok="salvo"):
        params = {}
        for key in ("q", "category", "status", "period", "page"):
            raw = str(form.get(key, "") or "").strip()
            if raw:
                params[key] = raw[:150]
        params["ok"] = ok
        if next_id is not None and next_id > 0:
            params["open"] = str(next_id)
        return "/painel/todos-produtos?" + urlencode(params) + "#lista-produtos455"

    @app.get("/painel/todos-produtos", response_class=HTMLResponse)
    def all_products455(request: Request, q: str = "", category: str = "", status: str = "all",
                        period: str = "30", page: int = 1, open: int = 0):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            products = [dict(r) for r in conn.execute(
                "SELECT * FROM products WHERE professional_id=?", (pro["id"],)).fetchall()]
            categories = [dict(r) for r in conn.execute(
                "SELECT name FROM product_categories WHERE professional_id=? AND active=1 ORDER BY sort_order,id",
                (pro["id"],)).fetchall()]
            subcategories = [dict(r) for r in nowup_subcategories448.rows(conn, pro["id"]) if r["active"]]
            period = period if period in PERIODS else "30"
            status = status if status in ("all", "active", "inactive", "no-stock") else "all"
            performance = _sales(conn, pro["id"], period)
            photos = {p["id"]: p["image_filename"] for p in products if p["is_group_header260"]}
            parents = {p["id"]: p["name"] for p in products if p["is_group_header260"]}
            inventory = {}
            try:
                inventory = {int(r["product_id"]): int(r["qty"]) for r in conn.execute(
                    """SELECT fi.product_id,SUM(fi.on_hand) qty
                       FROM fashion_inventory391 fi JOIN products p ON p.id=fi.product_id
                       WHERE p.professional_id=? GROUP BY fi.product_id""", (pro["id"],)).fetchall()}
            except Exception:
                pass
            by_id = {p["id"]: p for p in products}
            for p in products:
                try:
                    p["updated_display455"] = datetime.fromisoformat(p["updated_at"]).astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M")
                except (ValueError, TypeError):
                    p["updated_display455"] = str(p["updated_at"])[:16]
                if p["group_parent_id260"] and not p["image_filename"]:
                    p["display_image455"] = photos.get(p["group_parent_id260"], "")
                else:
                    p["display_image455"] = p["image_filename"]
                p["group_name455"] = parents.get(p["group_parent_id260"], "")
                p["related_ids455"] = _ids(p.get("related256", ""))
                p["stats455"] = performance.get(p["id"], {"sold": 0, "revenue": 0, "cancelled": 0, "days": 0}).copy()
                if p["is_group_header260"]:
                    children = [item for item in products if item["group_parent_id260"] == p["id"]]
                    p["stats455"] = {key: sum(performance.get(item["id"], {}).get(key, 0) for item in children) for key in ("sold", "revenue", "cancelled")}
                    p["stats455"]["days"] = 0  # Group-cover days are not a sum of child days.
                p["inventory455"] = inventory.get(p["id"])
                p["status455"] = ("Indisponível" if not p["available"] else
                                  "Sem estoque" if p["inventory455"] is not None and p["inventory455"] <= 0 else "Ativo")
            filter_q = _fold(q[:140])
            visible = [p for p in products if
                       (not category or _fold(p["category"]) == _fold(category))
                       and (status == "all" or (status == "active" and p["status455"] == "Ativo")
                            or (status == "inactive" and p["status455"] == "Indisponível")
                            or (status == "no-stock" and p["status455"] == "Sem estoque"))
                       and (not filter_q or filter_q in _fold(p["name"] + " " + str(p["id"]) + " " + p["group_name455"]))]
            visible.sort(key=lambda p: (_fold(p["name"]), p["id"]))
            pages = max(1, math.ceil(len(visible) / PER_PAGE))
            page = max(1, min(page, pages))
            page_products = visible[(page - 1) * PER_PAGE: page * PER_PAGE]
            for i, p in enumerate(page_products):
                p["next455"] = (page_products[i + 1]["id"] if i + 1 < len(page_products)
                                else page_products[i - 1]["id"] if i else 0)
            if open and not any(p["id"] == open for p in page_products):
                open = 0
            history = {}
            try:
                if page_products:
                    ids = [p["id"] for p in page_products]
                    marker = ",".join("?" for _ in ids)
                    for entry in conn.execute(
                        "SELECT product_id,detail,created_at FROM product_audit455 WHERE professional_id=? AND product_id IN (" + marker + ") ORDER BY id DESC",
                        (pro["id"], *ids)).fetchall():
                        if len(history.get(entry["product_id"], [])) < 6:
                            record = dict(entry)
                            try:
                                record["fields455"] = ", ".join(json.loads(entry["detail"]).keys())
                            record["created_display455"] = datetime.fromisoformat(entry["created_at"]).astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M")
                            except (TypeError, ValueError):
                                record["fields455"] = "Edição registrada"
                            history.setdefault(entry["product_id"], []).append(record)
            except Exception:
                pass
            ranking = sorted((p for p in products if not p["is_group_header260"]),
                             key=lambda p: (-p["stats455"]["sold"], _fold(p["name"])))[:10]
            category_totals = {}
            for p in products:
                if p["is_group_header260"]:
                    continue
                rec = category_totals.setdefault(p["category"], {"sold": 0, "revenue": 0, "cancelled": 0})
                for field in rec:
                    rec[field] += p["stats455"][field]
            category_ranking = sorted(category_totals.items(), key=lambda row: -row[1]["revenue"])
            return templates.TemplateResponse("all_products455.html", context(
                request, pro=pro, products455=page_products, all_names455=[
                    {"id": p["id"], "name": p["name"]} for p in products if not p["is_group_header260"]],
                categories455=categories, subcategories455=subcategories,
                page455=page, pages455=pages, count455=len(visible), total455=len(products),
                q455=q[:140], category455=category, status455=status, period455=period, open455=open,
                history455=history, ranking455=ranking, category_ranking455=category_ranking,
                ok455=request.query_params.get("ok", "")),
                headers={"Cache-Control": "private, no-store"})
        finally:
            conn.close()

    @app.post("/painel/todos-produtos/{product_id}/editar")
    def product_edit455(request: Request, product_id: int, name: str = Form(...),
                        category: str = Form(""), subcategory_id261: int = Form(0),
                        price: str = Form(""), description: str = Form(""),
                        available: str | None = Form(None),
                        photo: UploadFile | None = File(None),
                        recommend256: str | None = Form(None),
                        related256: list[int] = Form([]), next_id: int = Form(0),
                        return_q455: str = Form(""), return_category455: str = Form(""),
                        return_status455: str = Form("all"), return_period455: str = Form("30"),
                        return_page455: int = Form(1)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            existing = conn.execute(
                "SELECT * FROM products WHERE id=? AND professional_id=?",
                (product_id, pro["id"])).fetchone()
            if not existing:
                raise HTTPException(404, "Produto não encontrado nesta loja.")
            old = dict(existing)
            clean = name.strip()[:140]
            if not clean:
                raise HTTPException(400, "Informe o nome do produto.")
            if old["group_parent_id260"]:
                # A group member always belongs to its parent's category.
                parent = conn.execute(
                    "SELECT category,subcategory_id261 FROM products WHERE id=? AND professional_id=? AND is_group_header260=1",
                    (old["group_parent_id260"], pro["id"])).fetchone()
                if not parent:
                    raise HTTPException(409, "Agrupador não encontrado.")
                cat = parent["category"]
                subcat = int(parent["subcategory_id261"] or 0)
            else:
                cat_row = conn.execute(
                    "SELECT name FROM product_categories WHERE professional_id=? AND lower(name)=lower(?) AND active=1",
                    (pro["id"], category.strip())).fetchone()
                if not cat_row:
                    raise HTTPException(400, "Selecione uma categoria ativa da loja.")
                cat = cat_row["name"]
                subcat = nowup_subcategories448.valid_selection(conn, pro["id"], cat, subcategory_id261)
            cents = 0 if old["is_group_header260"] else price_to_cents(price)
            if not old["is_group_header260"] and cents <= 0:
                raise HTTPException(400, "O preço deve ser maior que zero.")
            promo = int(old.get("promo_price_cents") or 0)
            if promo > 0 and cents <= promo and not old["is_group_header260"]:
                raise HTTPException(400, "Preço normal precisa ficar acima do preço promocional existente.")
            ids = [] if old["is_group_header260"] else [int(x) for x in related256]
            related = validate_pairs(conn, pro["id"], ids, product_id=product_id)
            if ids:
                placeholders = ",".join("?" for _ in ids)
                if conn.execute("SELECT COUNT(*) FROM products WHERE professional_id=? AND is_group_header260=1 AND id IN (" + placeholders + ")",
                                (pro["id"], *ids)).fetchone()[0]:
                    raise HTTPException(400, "Capas de agrupadores não podem ser sugeridas como produtos.")
            filename = save_image(photo) if photo and photo.filename else old["image_filename"]
            new = {"name": clean, "category": cat, "subcategory_id261": subcat,
                   "price_cents": cents, "description": description.strip()[:600],
                   "available": 1 if available else 0, "image_filename": filename,
                   "related256": related,
                   "recommend256": 1 if (recommend256 and not old["is_group_header260"]) else 0}
            if old["is_group_header260"]:
                # Changing the cover's category moves the whole group as in the original editor.
                new["related256"] = old["related256"]
                new["recommend256"] = old["recommend256"]
            changes = {field: {"antes": old[field], "depois": value} for field, value in new.items()
                       if old[field] != value}
            if changes:
                fields = ", ".join(field + "=?" for field in new)
                conn.execute("UPDATE products SET " + fields + ",updated_at=? WHERE id=? AND professional_id=?",
                             (*new.values(), now_iso(), product_id, pro["id"]))
                if old["is_group_header260"] and old["category"] != cat:
                    conn.execute("UPDATE products SET category=?,subcategory_id261=0,updated_at=? WHERE professional_id=? AND group_parent_id260=?",
                                 (cat, now_iso(), pro["id"], product_id))
                conn.execute("INSERT INTO product_audit455(professional_id,product_id,actor_id,detail,created_at) VALUES(?,?,?,?,?)",
                             (pro["id"], product_id, user["id"], json.dumps(changes, ensure_ascii=False), now_iso()))
                conn.commit()
            else:
                conn.commit()
            data = {"q": return_q455, "category": return_category455,
                    "status": return_status455, "period": return_period455,
                    "page": str(return_page455)}
            return RedirectResponse(return_url(data, next_id, "salvo"), 303)
        finally:
            conn.close()

    @app.post("/painel/todos-produtos/{product_id}/excluir")
    def product_delete455(request: Request, product_id: int, next_id: int = Form(0),
                          return_q455: str = Form(""), return_category455: str = Form(""),
                          return_status455: str = Form("all"), return_period455: str = Form("30"),
                          return_page455: int = Form(1)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            row = conn.execute("SELECT * FROM products WHERE id=? AND professional_id=?", (product_id, pro["id"])).fetchone()
            if not row:
                raise HTTPException(404, "Produto não encontrado.")
            if row["is_group_header260"]:
                conn.execute("""UPDATE products SET group_parent_id260=0,
                    image_filename=CASE WHEN image_filename='' THEN ? ELSE image_filename END,
                    updated_at=? WHERE professional_id=? AND group_parent_id260=?""",
                             (row["image_filename"], now_iso(), pro["id"], product_id))
            conn.execute("DELETE FROM products WHERE id=? AND professional_id=?", (product_id, pro["id"]))
            conn.commit()
            data = {"q": return_q455, "category": return_category455,
                    "status": return_status455, "period": return_period455,
                    "page": str(return_page455)}
            return RedirectResponse(return_url(data, next_id, "excluido"), 303)
        finally:
            conn.close()

    @app.post("/painel/todos-produtos/leve-junto-categoria")
    def bulk_pairs455(request: Request, category: str = Form(...), target_id: int = Form(...)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            category_row = conn.execute("SELECT name FROM product_categories WHERE professional_id=? AND active=1 AND lower(name)=lower(?)",
                                        (pro["id"], category)).fetchone()
            target = conn.execute("SELECT id,is_group_header260 FROM products WHERE professional_id=? AND id=?",
                                  (pro["id"], target_id)).fetchone()
            if not category_row or not target or target["is_group_header260"]:
                raise HTTPException(400, "Escolha uma categoria e um produto válido da sua loja.")
            rows = conn.execute("SELECT id,related256 FROM products WHERE professional_id=? AND category=? AND is_group_header260=0",
                                (pro["id"], category_row["name"])).fetchall()
            changed = 0
            for row in rows:
                if row["id"] == target_id:
                    continue
                related = _ids(row["related256"])
                if target_id in related or len(related) >= 20:
                    continue
                related.append(target_id)
                conn.execute("UPDATE products SET related256=?,updated_at=? WHERE id=? AND professional_id=?",
                             (",".join(map(str, related)), now_iso(), row["id"], pro["id"]))
                changed += 1
            conn.commit()
            return RedirectResponse("/painel/todos-produtos?" + urlencode({
                "category": category_row["name"], "ok": "leve-junto", "total": changed}) + "#leve-junto455", 303)
        finally:
            conn.close()

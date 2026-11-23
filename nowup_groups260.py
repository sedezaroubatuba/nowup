"""NowUp v260: product groups use real product IDs for stock, sales and checkout."""
import nowup_subcategories448
from datetime import date, datetime
from zoneinfo import ZoneInfo
from fastapi import Form, File, UploadFile, HTTPException, Request
from fastapi.responses import RedirectResponse


def migrate(conn, ensure_column):
    ensure_column(conn, "products", "group_parent_id260", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "products", "is_group_header260", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "products", "promo_start260", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "products", "promo_end260", "TEXT NOT NULL DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_products_group260 ON products(professional_id,group_parent_id260,id)")


def effective_promo_cents(product, today=None):
    """Read-only calculation; the checkout must never trust a browser promo price."""
    value = int(product["promo_price_cents"] or 0)
    normal = int(product["price_cents"] or 0)
    if not 0 < value < normal:
        return 0
    today = today or datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    return value if ((not product["promo_start260"] or product["promo_start260"] <= today)
                     and (not product["promo_end260"] or product["promo_end260"] >= today)) else 0


def public_catalog(rows, today=None):
    """Hide children from the top-level catalog; keep them as real sellable items."""
    expanded = []
    for row in rows:
        item = dict(row)
        item["promo_price_cents"] = effective_promo_cents(row, today)
        expanded.append(item)
    heads = {r["id"]: r for r in expanded if r["is_group_header260"]}
    grouped = {key: [] for key in heads}
    for item in expanded:
        parent_id = item["group_parent_id260"]
        if parent_id in heads:
            grouped[parent_id].append(item)
    # A group is visible only when enabled and at least one child can be purchased.
    visible = [p for p in expanded if (not p["group_parent_id260"] or p["group_parent_id260"] not in heads)
               and (not p["is_group_header260"] or
                    (p["available"] and any(c["available"] for c in grouped.get(p["id"], []))))]
    for parent_id, children in grouped.items():
        head = heads[parent_id]
        available = [child for child in children if child["available"]]
        head["group_min_price260"] = min(
            (child["promo_price_cents"] or child["price_cents"] for child in available),
            default=0,
        )
        cover = head.get("image_filename", "")
        for child in children:
            child["group_cover260"] = cover
            child["group_name260"] = heads[parent_id]["name"]
            if not child.get("image_filename"):
                child["image_filename"] = cover
    return visible, grouped


def panel_groups(rows):
    groups = []
    members = {}
    existing = []
    for product in rows:
        if product["is_group_header260"]:
            groups.append(product)
            members[product["id"]] = []
    for product in rows:
        if product["group_parent_id260"] in members:
            members[product["group_parent_id260"]].append(product)
        elif not product["is_group_header260"] and not product["group_parent_id260"]:
            existing.append(product)
    return [{"header": head,
             "items": sorted(members[head["id"]], key=lambda x: (x["sort_order"], x["id"])),
             "promo_item": next((item for item in members[head["id"]] if item["promo_price_cents"] > 0), None)}
            for head in groups], existing


def _valid_category(conn, owner, category):
    row = conn.execute(
        "SELECT name FROM product_categories WHERE professional_id=? AND lower(name)=lower(?) AND active=1",
        (owner, (category or "").strip()[:80]),
    ).fetchone()
    if not row:
        raise HTTPException(400, "Escolha uma categoria ativa da sua loja.")
    return row["name"]


def _group(conn, owner, group_id):
    row = conn.execute(
        "SELECT * FROM products WHERE id=? AND professional_id=? AND is_group_header260=1 AND group_parent_id260=0",
        (group_id, owner),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Agrupador não encontrado nesta loja.")
    return row


def _member(conn, owner, group_id, item_id):
    row = conn.execute(
        "SELECT * FROM products WHERE id=? AND professional_id=? AND group_parent_id260=? AND is_group_header260=0",
        (item_id, owner, group_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Item não pertence a este agrupador.")
    return row


def _redirect(group_id=None):
    if group_id:
        return RedirectResponse(f"/painel?ok=agrupador&grupo260={group_id}#grupo260-{group_id}", status_code=303)
    return RedirectResponse("/painel?ok=agrupador#agrupadores260", status_code=303)


def register(app, db, require_user, require_premium_catalog, save_image, price_to_cents, now_iso):

    @app.post("/painel/cardapio/agrupadores")
    def group_create260(request: Request, name: str = Form(...), category: str = Form(...),
                        subcategory_id261: int = Form(0), description: str = Form(""),
                        photo: UploadFile | None = File(None)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            clean = name.strip()[:140]
            if not clean:
                raise HTTPException(400, "Informe o nome do agrupador.")
            cat = _valid_category(conn, pro["id"], category)
            subcat = nowup_subcategories448.valid_selection(conn, pro["id"], cat, subcategory_id261)
            if not photo or not photo.filename:
                raise HTTPException(400, "Envie a foto de capa que será usada no agrupador.")
            fn = save_image(photo)
            created = now_iso()
            cur = conn.execute(
                """INSERT INTO products(professional_id,name,description,category,price_cents,image_filename,
                   available,created_at,updated_at,is_group_header260)
                   VALUES(?,?,?,?,0,?,1,?,?,1)""",
                (pro["id"], clean, description.strip()[:600], cat, fn, created, created),
            )
            group_id = cur.lastrowid
            conn.execute("UPDATE products SET subcategory_id261=? WHERE id=? AND professional_id=?",
                         (subcat, group_id, pro["id"]))
            conn.commit()
        finally:
            conn.close()
        return RedirectResponse(f"/painel?ok=agrupador&grupo260={group_id}#grupo260-{group_id}", 303)


    @app.post("/painel/cardapio/agrupadores/{group_id}")
    def group_edit260(request: Request, group_id: int, name: str = Form(...),
                      category: str = Form(...), subcategory_id261: int = Form(0), description: str = Form(""),
                      available: str | None = Form(None), photo: UploadFile | None = File(None)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            old = _group(conn, pro["id"], group_id)
            clean = name.strip()[:140]
            if not clean:
                raise HTTPException(400, "Informe o nome do agrupador.")
            cat = _valid_category(conn, pro["id"], category)
            subcat = nowup_subcategories448.valid_selection(conn, pro["id"], cat, subcategory_id261)
            fn = save_image(photo) if photo and photo.filename else old["image_filename"]
            conn.execute(
                """UPDATE products SET name=?,description=?,category=?,subcategory_id261=?,image_filename=?,available=?,updated_at=?
                   WHERE id=? AND professional_id=?""",
                (clean, description.strip()[:600], cat, subcat, fn, 1 if available else 0,
                 now_iso(), group_id, pro["id"]),
            )
            conn.execute("UPDATE products SET category=?,updated_at=? WHERE group_parent_id260=? AND professional_id=?",
                         (cat, now_iso(), group_id, pro["id"]))
            conn.commit()
        finally:
            conn.close()
        return _redirect(group_id)

    @app.post("/painel/cardapio/agrupadores/{group_id}/itens")
    def item_create260(request: Request, group_id: int, name: str = Form(...), price: str = Form(...),
                       available: str | None = Form(None), photo: UploadFile | None = File(None)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            head = _group(conn, pro["id"], group_id)
            clean = name.strip()[:140]
            cents = price_to_cents(price)
            if not clean or cents <= 0:
                raise HTTPException(400, "Informe o nome e um preço maior que zero.")
            fn = save_image(photo) if photo and photo.filename else ""
            created = now_iso()
            conn.execute(
                """INSERT INTO products(professional_id,name,description,category,price_cents,image_filename,
                   available,created_at,updated_at,group_parent_id260)
                   VALUES(?,?,'',?,?,?,?,?,?,?)""",
                (pro["id"], clean, head["category"], cents, fn,
                 1 if available else 0, created, created, group_id),
            )
            conn.commit()
        finally:
            conn.close()
        return _redirect(group_id)

    @app.post("/painel/cardapio/agrupadores/{group_id}/itens/{item_id}")
    def item_edit260(request: Request, group_id: int, item_id: int, name: str = Form(...),
                     price: str = Form(...), promo_price: str = Form(""),
                     available: str | None = Form(None), photo: UploadFile | None = File(None)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            _group(conn, pro["id"], group_id)
            item = _member(conn, pro["id"], group_id, item_id)
            clean = name.strip()[:140]
            cents = price_to_cents(price)
            if not clean or cents <= 0:
                raise HTTPException(400, "Informe o nome e um preço maior que zero.")
            fn = save_image(photo) if photo and photo.filename else item["image_filename"]
            # A manual promotion changes only this flavor, not the entire group.
            promo = price_to_cents(promo_price) if promo_price.strip() else 0
            if promo and promo >= cents:
                raise HTTPException(400, "O preço promocional precisa ser menor que o preço normal.")
            conn.execute(
                """UPDATE products SET name=?,price_cents=?,promo_price_cents=?,
                   promo_start260=?,promo_end260=?,image_filename=?,available=?,updated_at=?
                   WHERE id=? AND professional_id=?""",
                (clean, cents, promo,
                 item["promo_start260"] if promo else "", item["promo_end260"] if promo else "",
                 fn, 1 if available else 0, now_iso(), item_id, pro["id"]),
            )
            conn.commit()
        finally:
            conn.close()
        return _redirect(group_id)

    @app.post("/painel/cardapio/agrupadores/{group_id}/itens/{item_id}/disponibilidade")
    def item_available260(request: Request, group_id: int, item_id: int, available: int = Form(...)):
        if available not in (0, 1):
            raise HTTPException(400, "Disponibilidade inválida.")
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            _group(conn, pro["id"], group_id)
            _member(conn, pro["id"], group_id, item_id)
            conn.execute("UPDATE products SET available=?,updated_at=? WHERE id=?",
                         (available, now_iso(), item_id))
            conn.commit()
        finally:
            conn.close()
        return _redirect(group_id)

    @app.post("/painel/cardapio/agrupadores/{group_id}/vincular")
    def item_link260(request: Request, group_id: int, item_id: int = Form(...)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            head = _group(conn, pro["id"], group_id)
            changed = conn.execute(
                """UPDATE products SET group_parent_id260=?,category=?,subcategory_id261=0,updated_at=?
                   WHERE id=? AND professional_id=? AND group_parent_id260=0 AND is_group_header260=0""",
                (group_id, head["category"], now_iso(), item_id, pro["id"]),
            ).rowcount
            if not changed:
                raise HTTPException(404, "Produto existente não encontrado ou já agrupado.")
            conn.commit()
        finally:
            conn.close()
        return _redirect(group_id)

    @app.post("/painel/cardapio/agrupadores/{group_id}/itens/{item_id}/desvincular")
    def item_unlink260(request: Request, group_id: int, item_id: int):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            _group(conn, pro["id"], group_id)
            _member(conn, pro["id"], group_id, item_id)
            conn.execute("UPDATE products SET group_parent_id260=0,updated_at=? WHERE id=?",
                         (now_iso(), item_id))
            conn.commit()
        finally:
            conn.close()
        return _redirect(group_id)

    @app.post("/painel/cardapio/agrupadores/{group_id}/promocao")
    def group_promotion260(request: Request, group_id: int, item_ids: list[int] = Form([]),
                           promo_price: str = Form(""), promo_start: str = Form(""),
                           promo_end: str = Form("")):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            _group(conn, pro["id"], group_id)
            members = conn.execute(
                "SELECT id,price_cents FROM products WHERE professional_id=? AND group_parent_id260=?",
                (pro["id"], group_id),
            ).fetchall()
            by_id = {row["id"]: row for row in members}
            chosen = set(item_ids)
            if not chosen.issubset(by_id.keys()):
                raise HTTPException(400, "Há itens selecionados que não pertencem ao agrupador.")
            cents = price_to_cents(promo_price) if chosen else 0
            if chosen and (not 0 < cents or any(cents >= by_id[item]["price_cents"] for item in chosen)):
                raise HTTPException(400, "O preço promocional deve ser menor que o preço normal de todos os itens escolhidos.")
            for raw in (promo_start, promo_end):
                if raw:
                    try:
                        date.fromisoformat(raw)
                    except ValueError:
                        raise HTTPException(400, "Data da promoção inválida.")
            if promo_start and promo_end and promo_start > promo_end:
                raise HTTPException(400, "A data inicial não pode ser posterior à final.")
            # Saving a selection replaces the old selection; unchecked flavors keep full price.
            conn.execute(
                """UPDATE products SET promo_price_cents=0,promo_start260='',promo_end260='',updated_at=?
                   WHERE professional_id=? AND group_parent_id260=?""",
                (now_iso(), pro["id"], group_id),
            )
            for item_id in chosen:
                conn.execute(
                    """UPDATE products SET promo_price_cents=?,promo_start260=?,promo_end260=?,updated_at=?
                       WHERE id=? AND professional_id=? AND group_parent_id260=?""",
                    (cents, promo_start, promo_end, now_iso(), item_id, pro["id"], group_id),
                )
            conn.commit()
        finally:
            conn.close()
        return _redirect(group_id)

    @app.post("/painel/cardapio/agrupadores/{group_id}/excluir")
    def group_delete260(request: Request, group_id: int):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            _group(conn, pro["id"], group_id)
            # Preserve stock, old order references and products if the group is removed.
            conn.execute("UPDATE products SET group_parent_id260=0,updated_at=? WHERE professional_id=? AND group_parent_id260=?",
                         (now_iso(), pro["id"], group_id))
            conn.execute("DELETE FROM products WHERE id=? AND professional_id=? AND is_group_header260=1",
                         (group_id, pro["id"]))
            conn.commit()
        finally:
            conn.close()
        return _redirect(group_id)

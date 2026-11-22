"""NowUp v261: optional subcategories under each store's product categories.

Categories remain the parent navigation; grouping does not replace product IDs,
existing category names, cart quantities, or products grouped by flavor (v260).
"""
import sqlite3
from fastapi import Form, HTTPException, Request
from fastapi.responses import RedirectResponse


def migrate(conn, ensure_column):
    ensure_column(conn, "products", "subcategory_id261", "INTEGER NOT NULL DEFAULT 0")
    conn.execute("""CREATE TABLE IF NOT EXISTS product_subcategories261(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
        category_id INTEGER NOT NULL REFERENCES product_categories(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 100,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        UNIQUE(professional_id,category_id,name)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_subcategory261_owner ON product_subcategories261(professional_id,category_id,active,sort_order,id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_subcategory261_product ON products(professional_id,subcategory_id261)")


def category_for_owner(conn, professional_id, category_id, active=False):
    extra = " AND active=1" if active else ""
    row = conn.execute(
        "SELECT * FROM product_categories WHERE id=? AND professional_id=?" + extra,
        (category_id, professional_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Categoria não encontrada nesta loja.")
    return row


def subcategory_for_owner(conn, professional_id, subcategory_id):
    row = conn.execute(
        "SELECT * FROM product_subcategories261 WHERE id=? AND professional_id=?",
        (subcategory_id, professional_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Subcategoria não encontrada nesta loja.")
    return row


def valid_selection(conn, professional_id, category_name, subcategory_id):
    """Accept 0 to leave ungrouped; otherwise enforce the same store and parent."""
    if not subcategory_id:
        return 0
    row = conn.execute(
        """SELECT sc.id FROM product_subcategories261 sc
           JOIN product_categories pc ON pc.id=sc.category_id
           WHERE sc.id=? AND sc.professional_id=? AND sc.active=1
             AND pc.professional_id=? AND pc.active=1 AND lower(pc.name)=lower(?)""",
        (subcategory_id, professional_id, professional_id, (category_name or "").strip()),
    ).fetchone()
    if not row:
        raise HTTPException(400, "Escolha uma subcategoria ativa da categoria selecionada.")
    return row["id"]


def rows(conn, professional_id):
    return conn.execute(
        """SELECT s.*,pc.name AS category_name FROM product_subcategories261 s
           JOIN product_categories pc ON pc.id=s.category_id
           WHERE s.professional_id=? AND pc.professional_id=?
           ORDER BY pc.sort_order,pc.id,s.sort_order,s.id""",
        (professional_id, professional_id),
    ).fetchall()


def public_rows(conn, professional_id):
    """Only active groups from active parents are offered to shoppers."""
    return conn.execute(
        """SELECT s.id,s.category_id,s.name,pc.name AS category_name
           FROM product_subcategories261 s JOIN product_categories pc ON pc.id=s.category_id
           WHERE s.professional_id=? AND pc.professional_id=? AND s.active=1 AND pc.active=1
           ORDER BY pc.sort_order,s.sort_order,s.id""",
        (professional_id, professional_id),
    ).fetchall()


def _go():
    return RedirectResponse("/painel?ok=subcategoria#categorias-loja", 303)


def register(app, db, require_user, require_premium_catalog, now_iso):

    @app.post("/painel/cardapio/subcategorias261")
    def add261(request: Request, category_id: int = Form(...), name: str = Form(...)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            category_for_owner(conn, pro["id"], category_id, active=True)
            clean = name.strip()[:80]
            if not clean:
                raise HTTPException(400, "Informe o nome da subcategoria.")
            count = conn.execute(
                "SELECT COUNT(*) FROM product_subcategories261 WHERE professional_id=? AND category_id=?",
                (pro["id"], category_id),
            ).fetchone()[0]
            if count >= 80:
                raise HTTPException(400, "Limite de 80 subcategorias por categoria.")
            order = conn.execute(
                "SELECT COALESCE(MAX(sort_order),0)+1 FROM product_subcategories261 WHERE professional_id=? AND category_id=?",
                (pro["id"], category_id),
            ).fetchone()[0]
            try:
                conn.execute(
                    "INSERT INTO product_subcategories261(professional_id,category_id,name,sort_order,created_at) VALUES(?,?,?,?,?)",
                    (pro["id"], category_id, clean, order, now_iso()),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise HTTPException(409, "Já existe uma subcategoria com esse nome nesta categoria.")
        finally:
            conn.close()
        return _go()

    @app.post("/painel/cardapio/subcategorias261/{subcategory_id}")
    def edit261(request: Request, subcategory_id: int, name: str = Form(...),
                active: str | None = Form(None), sort_order: int = Form(100)):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            sc = subcategory_for_owner(conn, pro["id"], subcategory_id)
            clean = name.strip()[:80]
            if not clean:
                raise HTTPException(400, "Informe o nome da subcategoria.")
            try:
                conn.execute(
                    """UPDATE product_subcategories261 SET name=?,active=?,sort_order=?
                       WHERE id=? AND professional_id=? AND category_id=?""",
                    (clean, 1 if active else 0, max(1, min(9999, sort_order)), sc["id"],
                     pro["id"], sc["category_id"]),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise HTTPException(409, "Já existe uma subcategoria com esse nome nesta categoria.")
        finally:
            conn.close()
        return _go()

    @app.post("/painel/cardapio/subcategorias261/{subcategory_id}/excluir")
    def delete261(request: Request, subcategory_id: int):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            sc = subcategory_for_owner(conn, pro["id"], subcategory_id)
            # Never delete the products: just return them to the parent category.
            conn.execute("UPDATE products SET subcategory_id261=0,updated_at=? WHERE professional_id=? AND subcategory_id261=?",
                         (now_iso(), pro["id"], sc["id"]))
            conn.execute("DELETE FROM product_subcategories261 WHERE id=? AND professional_id=?",
                         (sc["id"], pro["id"]))
            conn.commit()
        finally:
            conn.close()
        return _go()

    @app.post("/painel/cardapio/subcategorias261/organizar")
    def bulk_assign261(request: Request, category_id: int = Form(...),
                       subcategory_id: int = Form(0), product_ids: list[int] = Form([])):
        user = require_user(request, "professional")
        conn = db()
        try:
            pro = require_premium_catalog(conn, user["id"])
            category = category_for_owner(conn, pro["id"], category_id, active=True)
            sc_id = valid_selection(conn, pro["id"], category["name"], subcategory_id)
            ids = sorted(set(product_ids))
            if len(ids) > 1000:
                raise HTTPException(400, "Organize até mil produtos por vez.")
            if ids:
                placeholders = ",".join("?" for _ in ids)
                current = conn.execute(
                    f"""SELECT id FROM products WHERE id IN ({placeholders}) AND professional_id=?
                        AND lower(category)=lower(?) AND group_parent_id260=0""",
                    (*ids, pro["id"], category["name"]),
                ).fetchall()
                if len(current) != len(ids):
                    raise HTTPException(400, "A seleção contém produto de outra categoria, loja ou um item interno.")
                conn.execute(
                    f"""UPDATE products SET subcategory_id261=?,updated_at=?
                        WHERE professional_id=? AND id IN ({placeholders})""",
                    (sc_id, now_iso(), pro["id"], *ids),
                )
                conn.commit()
        finally:
            conn.close()
        return _go()

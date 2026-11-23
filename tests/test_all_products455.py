"""V455: isolated tests for the independent all-products merchant page."""
from datetime import datetime, timezone
from test_merchant228 import env
from nowup_allproducts455 import _sales, _fold


def make_products(m, owner, count=12):
    ids = []
    with m.db() as conn:
        conn.execute("INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",
                     (owner, "Cervejas", 2, 1, m.now_iso()))
        for i in range(count):
            row = conn.execute("""INSERT INTO products(
                professional_id,name,category,price_cents,available,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?)""",
                (owner, "Bebida " + str(i).zfill(2), "Cervejas", 400, 1, m.now_iso(), m.now_iso()))
            ids.append(row.lastrowid)
        conn.commit()
    return ids


def test_page_is_ten_alphabetical_items_with_owner_guard(env):
    m, client, _, store, other = env
    ids = make_products(m, store)
    with m.db() as conn:
        conn.execute("""INSERT INTO products(professional_id,name,category,price_cents,available,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?)""", (other, "PRIVATE OTHER STORE", "Cervejas", 100, 1, m.now_iso(), m.now_iso()))
        conn.commit()
    response = client.get("/painel/todos-produtos?q=Bebida&category=Cervejas")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.text.count('class="nu455-item"') == 10
    assert "Bebida 00" in response.text and "Bebida 09" in response.text
    assert f'id="produto-{ids[10]}"' not in response.text  # Global Leve Junto picker still contains all names.
    assert "PRIVATE OTHER STORE" not in response.text
    next_page = client.get("/painel/todos-produtos?q=Bebida&category=Cervejas&page=2")
    assert next_page.status_code == 200 and "Bebida 10" in next_page.text
    assert "10" in response.text
    summary = response.text.split('<details class="nu455-item"', 1)[1].split('</summary>', 1)[0]
    assert "<img" not in summary  # The site header may contain its own logo image.
    assert _fold("Água 500ml") == "agua 500ml"
    assert m.app is not None
    assert ids


def test_product_save_keeps_category_price_and_next_page(env):
    m, client, _, store, _ = env
    with m.db() as conn:
        product = conn.execute("SELECT id FROM products WHERE professional_id=? AND name='Bebida 00'",(store,)).fetchone()
    assert product
    pid = product["id"]
    response = client.post(f"/painel/todos-produtos/{pid}/editar", data={
        "name":"Bebida 00 Alterada",
        "category":"Cervejas",
        "subcategory_id261":"0",
        "price":"7,50",
        "description":"Alterada no painel",
        "available":"1",
        "return_q455":"Bebida", "return_category455":"Cervejas",
        "return_status455":"all", "return_period455":"30",
        "return_page455":"2", "next_id":"0",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "page=2" in response.headers["location"] and "category=Cervejas" in response.headers["location"]
    with m.db() as conn:
        saved = conn.execute("SELECT name,category,price_cents,description FROM products WHERE id=?",(pid,)).fetchone()
        changes = conn.execute("SELECT COUNT(*) FROM product_audit455 WHERE professional_id=? AND product_id=?",(store,pid)).fetchone()[0]
    assert saved["name"] == "Bebida 00 Alterada" and saved["price_cents"] == 750
    assert saved["description"] == "Alterada no painel" and changes >= 1


def test_product_cannot_cross_merchant_boundary(env):
    m, client, _, store, other = env
    with m.db() as conn:
        other_id = conn.execute("SELECT id FROM products WHERE professional_id=? AND name='PRIVATE OTHER STORE'",(other,)).fetchone()["id"]
    assert client.post(f"/painel/todos-produtos/{other_id}/editar", data={
        "name":"Invasão", "category":"Cervejas", "price":"4,00"
    }, follow_redirects=False).status_code == 404
    assert client.post(f"/painel/todos-produtos/{other_id}/excluir", follow_redirects=False).status_code == 404
    with m.db() as conn:
        assert conn.execute("SELECT name FROM products WHERE id=?", (other_id,)).fetchone()[0] == "PRIVATE OTHER STORE"


def test_completed_vs_cancelled_sales_are_not_mixed(env):
    m, _, _, store, _ = env
    with m.db() as conn:
        pid = conn.execute("SELECT id FROM products WHERE professional_id=? AND name='Bebida 01'",(store,)).fetchone()["id"]
        for state, qty in (("completed",3),("cancelled",2),("new",100)):
            now = datetime.now(timezone.utc).isoformat()
            result = conn.execute("""INSERT INTO orders(professional_id,customer_name,status,total_cents,created_at,updated_at)
                VALUES(?,?,?,?,?,?)""", (store,"Cliente",state,qty*450,now,now))
            conn.execute("""INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price_cents)
                VALUES(?,?,?,?,?)""", (result.lastrowid,pid,"Bebida 01",qty,450))
        conn.commit()
        metrics = _sales(conn,store,"all")
    assert metrics[pid]["sold"] == 3
    assert metrics[pid]["cancelled"] == 2
    assert metrics[pid]["revenue"] == 1350
    assert metrics[pid]["days"] == 1


def test_bulk_pairs_do_not_modify_other_shops(env):
    m, client, _, store, other = env
    with m.db() as conn:
        target = conn.execute("SELECT id FROM products WHERE professional_id=? AND name='Bebida 02'",(store,)).fetchone()["id"]
        outside = conn.execute("SELECT id FROM products WHERE professional_id=? AND name='PRIVATE OTHER STORE'",(other,)).fetchone()["id"]
    bad = client.post("/painel/todos-produtos/leve-junto-categoria",
                      data={"category":"Cervejas", "target_id":outside},follow_redirects=False)
    assert bad.status_code == 400
    ok = client.post("/painel/todos-produtos/leve-junto-categoria",
                     data={"category":"Cervejas", "target_id":target},follow_redirects=False)
    assert ok.status_code == 303
    with m.db() as conn:
        rows = conn.execute("SELECT id,related256 FROM products WHERE professional_id=? AND category='Cervejas'",(store,)).fetchall()
        assert any(str(target) in (r["related256"] or "").split(",") for r in rows if r["id"] != target)
        assert conn.execute("SELECT related256 FROM products WHERE id=?",(outside,)).fetchone()[0] == ""


def test_group_cover_edit_changes_children_category_without_deleting_them(env):
    m, client, _, store, _ = env
    with m.db() as conn:
        head = conn.execute("""INSERT INTO products(
            professional_id,name,category,price_cents,is_group_header260,available,created_at,updated_at)
            VALUES(?,?,?,0,1,1,?,?)""", (store,"Capa de Sabores","Cervejas",m.now_iso(),m.now_iso())).lastrowid
        child = conn.execute("""INSERT INTO products(
            professional_id,name,category,price_cents,group_parent_id260,available,created_at,updated_at)
            VALUES(?,?,?,?,?,1,?,?)""",(store,"Sabor Uva","Cervejas",550,head,m.now_iso(),m.now_iso())).lastrowid
        conn.execute("INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",
                     (store,"Mercearia",3,1,m.now_iso()))
        conn.commit()
    result = client.post(f"/painel/todos-produtos/{head}/editar", data={
        "name":"Capa de Sabores","category":"Mercearia","description":"Capa","available":"1"
    }, follow_redirects=False)
    assert result.status_code == 303
    with m.db() as conn:
        assert conn.execute("SELECT category FROM products WHERE id=?",(child,)).fetchone()[0] == "Mercearia"
    result = client.post(f"/painel/todos-produtos/{head}/excluir", follow_redirects=False)
    assert result.status_code == 303
    with m.db() as conn:
        saved = conn.execute("SELECT group_parent_id260 FROM products WHERE id=?",(child,)).fetchone()
        assert saved and saved["group_parent_id260"] == 0

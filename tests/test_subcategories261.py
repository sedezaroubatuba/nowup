"""NowUp v261: optional product subcategories, without changing default storefront or existing sales."""
import importlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    directory=tmp_path_factory.mktemp("subcategories261")
    m=importlib.import_module("app")
    m.DB_PATH=Path(directory/"subcats.db")
    m.UPLOAD_DIR=Path(directory/"uploads")
    m.UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    m.init_db()
    m.nowup_sales107.initialize()
    with m.db() as conn:
        stores=conn.execute("SELECT id,user_id,slug FROM professionals ORDER BY id LIMIT 2").fetchall()
        assert len(stores)>=2
        for idx,p in enumerate(stores):
            conn.execute("UPDATE professionals SET plan_active='ambos',is_premium=1,offer_mode='menu' WHERE id=?",(p['id'],))
            expires=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
            conn.execute("INSERT INTO sessions(token,user_id,expires_at,absolute_expires_at238) VALUES(?,?,?,?)",
                         (f"sc261_{idx}",p['user_id'],expires,expires))
            for cat in ("Tabacaria","Bebidas Não Alcoólicas"):
                conn.execute("INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",
                             (p['id'],cat,10,1,m.now_iso()))
        conn.commit()
        cats=conn.execute("SELECT id,name FROM product_categories WHERE professional_id=? AND name IN ('Tabacaria','Bebidas Não Alcoólicas')",
                          (stores[0]['id'],)).fetchall()
        categories={row['name']:row['id'] for row in cats}
    client=TestClient(m.app,headers={"Origin":"http://testserver"})
    client.cookies.set("nowup_session","sc261_0")
    other=TestClient(m.app,headers={"Origin":"http://testserver"})
    other.cookies.set("nowup_session","sc261_1")
    return m,client,other,stores,categories


def test_parent_first_create_and_client_default(env):
    m,client,_,stores,categories=env
    id1=categories["Tabacaria"]
    id2=categories["Bebidas Não Alcoólicas"]
    for category_id,name in [(id1,"Sedas"),(id1,"Tabacos"),(id2,"Sucos")]:
        response=client.post("/painel/cardapio/subcategorias261",
            data={"category_id":category_id,"name":name},follow_redirects=False)
        assert response.status_code==303
    with m.db() as c:
        cat1=c.execute("SELECT id FROM product_subcategories261 WHERE category_id=? AND name='Sedas'",(id1,)).fetchone()[0]
        cat2=c.execute("SELECT id FROM product_subcategories261 WHERE category_id=? AND name='Sucos'",(id2,)).fetchone()[0]
    response=client.post("/painel/cardapio/produtos",data={
        "name":"Seda RAW","description":"Seda clássica","category":"Tabacaria",
        "subcategory_id261":str(cat1),"price":"5,00","available":"1","extras_mode":"none"
    },follow_redirects=False)
    assert response.status_code==303
    # No subcategory is required for a regular product, and catalog still renders all.
    response=client.post("/painel/cardapio/produtos",data={
        "name":"Piteira sem grupo","category":"Tabacaria",
        "price":"4,00","available":"1","extras_mode":"none"
    },follow_redirects=False)
    assert response.status_code==303
    url=f"/p/{stores[0]['slug']}/menu"
    html=client.get(url).text
    assert "Seda RAW" in html and "Piteira sem grupo" in html
    assert 'data-scid261="'+str(cat1)+'"' in html
    assert 'data-subcategory261="'+str(cat1)+'"' in html
    assert 'data-subcategory261="0"' in html
    # The filter is a collapsed client interaction, never a default item exclusion.
    js=m.BASE.joinpath("static/storefront187.js").read_text()
    assert "selectedSubcategory261=''" in js
    assert "subcatFilterList261.hidden=true" in js
    assert "source.dataset.subcategory261===selectedSubcategory261" in js
    admin=client.get("/painel").text
    assert "Escolha uma categoria" in admin and "Adicionar subcategoria" in admin
    assert "data-subcats-content261 hidden" in admin
    return cat1,cat2


def test_category_scoping_and_cross_store_protection(env):
    m,client,other,stores,categories=env
    with m.db() as c:
        sc=c.execute("SELECT id FROM product_subcategories261 WHERE category_id=? AND name='Sedas'",
                     (categories['Tabacaria'],)).fetchone()[0]
        product=c.execute("SELECT id FROM products WHERE professional_id=? AND name='Seda RAW'",
                          (stores[0]['id'],)).fetchone()[0]
    # Selecting a Seda subcategory under Beverages must be rejected.
    bad=client.post("/painel/cardapio/produtos",data={
        "name":"Wrong category","category":"Bebidas Não Alcoólicas",
        "subcategory_id261":str(sc),"price":"5,00","available":"1","extras_mode":"none"
    },follow_redirects=False)
    assert bad.status_code==400
    # Another merchant cannot edit or delete this store's subcategories.
    assert other.post(f"/painel/cardapio/subcategorias261/{sc}",
        data={"name":"Outra loja","active":"1"},follow_redirects=False).status_code==404
    assert other.post("/painel/cardapio/subcategorias261/organizar",
        data={"category_id":categories["Tabacaria"],"subcategory_id":str(sc),
              "product_ids":str(product)},follow_redirects=False).status_code==404
    with m.db() as c:
        assert c.execute("SELECT name FROM product_subcategories261 WHERE id=?",(sc,)).fetchone()[0]=="Sedas"


def test_bulk_reorganization_grouped_header_and_deletion(env):
    m,client,_,stores,categories=env
    with m.db() as c:
        sc=c.execute("SELECT id FROM product_subcategories261 WHERE category_id=? AND name='Sedas'",
                     (categories["Tabacaria"],)).fetchone()[0]
        product=c.execute("SELECT id FROM products WHERE professional_id=? AND name='Piteira sem grupo'",
                          (stores[0]['id'],)).fetchone()[0]
    changed=client.post("/painel/cardapio/subcategorias261/organizar",data={
        "category_id":categories["Tabacaria"],"subcategory_id":str(sc),"product_ids":str(product)
    },follow_redirects=False)
    assert changed.status_code==303
    with m.db() as c:
        assert c.execute("SELECT subcategory_id261 FROM products WHERE id=?",(product,)).fetchone()[0]==sc
    created=client.post("/painel/cardapio/agrupadores",data={
        "name":"Sedas premium","category":"Tabacaria","subcategory_id261":str(sc)
    },follow_redirects=False)
    assert created.status_code==303
    with m.db() as c:
        header=c.execute("SELECT id,subcategory_id261 FROM products WHERE professional_id=? AND is_group_header260=1 ORDER BY id DESC LIMIT 1",
            (stores[0]['id'],)).fetchone()
        assert header["subcategory_id261"]==sc
    response=client.post(f"/painel/cardapio/subcategorias261/{sc}/excluir",follow_redirects=False)
    assert response.status_code==303
    with m.db() as c:
        assert c.execute("SELECT subcategory_id261 FROM products WHERE id=?",(product,)).fetchone()[0]==0
        assert c.execute("SELECT subcategory_id261 FROM products WHERE id=?",(header['id'],)).fetchone()[0]==0
        assert c.execute("SELECT COUNT(*) FROM products WHERE id IN (?,?)",(product,header['id'])).fetchone()[0]==2

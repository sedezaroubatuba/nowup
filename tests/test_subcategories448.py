"""V448 regression: optional parent-scoped subcategories on the current production branch."""
import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    directory=tmp_path_factory.mktemp("subcat448")
    m=importlib.import_module("app")
    import cms, admin_customization, email_verification
    patch=pytest.MonkeyPatch()
    patch.setenv("NOWUP_DB_ENGINE","sqlite")
    patch.setenv("NOWUP_ADMIN_EMAIL","test-admin448@example.invalid")
    patch.setenv("NOWUP_ADMIN_PASSWORD","isolated-test-448-password")
    db_path=directory/"nowup.db"
    uploads=directory/"uploads";uploads.mkdir(exist_ok=True)
    for module in (m,cms,admin_customization,email_verification):
        patch.setattr(module,"DB_PATH",db_path)
    patch.setattr(m,"UPLOAD_DIR",uploads)
    patch.setattr(cms,"UPLOAD_DIR",uploads)
    for callback in m.app.router.on_startup:
        if callback.__name__ != "start":
            callback()
    with m.db() as conn:
        stores=conn.execute("SELECT id,user_id,slug FROM professionals ORDER BY id LIMIT 2").fetchall()
        assert len(stores)==2
        for i,store in enumerate(stores):
            conn.execute("UPDATE professionals SET plan_active='completo',is_premium=1,offer_mode='menu' WHERE id=?",(store["id"],))
            conn.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",
                         (f"subcat448-{i}",store["user_id"],(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()))
            for category in ("Tabacaria","Bebidas não alcoólicas"):
                conn.execute("INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",
                             (store["id"],category,20,1,m.now_iso()))
        conn.commit()
        cats=conn.execute("SELECT id,name FROM product_categories WHERE professional_id=? AND name IN (?,?)",
            (stores[0]["id"],"Tabacaria","Bebidas não alcoólicas")).fetchall()
        category_ids={row["name"]:row["id"] for row in cats}
    client=TestClient(m.app,headers={"Origin":"http://testserver"})
    client.cookies.set("nowup_session","subcat448-0")
    other=TestClient(m.app,headers={"Origin":"http://testserver"})
    other.cookies.set("nowup_session","subcat448-1")
    yield m,client,other,stores,category_ids
    client.close();other.close();patch.undo()


def test_create_and_unfiltered_catalog(env):
    m,client,_,stores,cats=env
    for cid,name in [(cats["Tabacaria"],"Sedas"),(cats["Tabacaria"],"Tabacos"),(cats["Bebidas não alcoólicas"],"Sucos")]:
        response=client.post("/painel/cardapio/subcategorias261",
                             data={"category_id":cid,"name":name},follow_redirects=False)
        assert response.status_code==303
    with m.db() as conn:
        seda=conn.execute("SELECT id FROM product_subcategories261 WHERE professional_id=? AND name='Sedas'",
                         (stores[0]["id"],)).fetchone()
    assert seda
    for name,subcategory in [("Seda de teste 448",seda["id"]),("Piteira sem filtro 448",0)]:
        response=client.post("/painel/cardapio/produtos",
            data={"name":name,"category":"Tabacaria","subcategory_id261":str(subcategory),
                  "price":"5,00","available":"1","extras_mode":"none"},follow_redirects=False)
        assert response.status_code==303
    menu=client.get(f"/p/{stores[0]['slug']}/menu")
    assert menu.status_code==200
    assert "Seda de teste 448" in menu.text and "Piteira sem filtro 448" in menu.text
    assert f'data-scid261="{seda["id"]}"' in menu.text
    assert f'data-subcategory261="{seda["id"]}"' in menu.text
    assert 'data-subcategory261="0"' in menu.text
    panel=client.get("/painel")
    assert panel.status_code==200
    assert "Escolha uma categoria" in panel.text
    assert "Adicionar subcategoria" in panel.text
    assert 'data-subcats-content261 hidden' in panel.text
    assert "data-subcat-picker261" in panel.text
    script=(m.BASE/"static"/"storefront187.js").read_text()
    assert "selectedSubcategory261=''" in script
    assert "subcatOptions261.hidden=true" in script


def test_invalid_parent_and_cross_store_are_rejected(env):
    m,client,other,stores,cats=env
    with m.db() as conn:
        seda=conn.execute("SELECT id FROM product_subcategories261 WHERE professional_id=? AND name='Sedas'",
                         (stores[0]["id"],)).fetchone()[0]
    invalid=client.post("/painel/cardapio/produtos",data={
        "name":"Não deve salvar","category":"Bebidas não alcoólicas",
        "subcategory_id261":str(seda),"price":"7,00","available":"1","extras_mode":"none"
    },follow_redirects=False)
    assert invalid.status_code==400
    with m.db() as conn:
        assert not conn.execute("SELECT id FROM products WHERE name='Não deve salvar' AND professional_id=?",
                                (stores[0]["id"],)).fetchone()
    assert other.post(f"/painel/cardapio/subcategorias261/{seda}",
        data={"name":"Tentativa de outra loja","active":"1"},follow_redirects=False).status_code==404
    assert other.post("/painel/cardapio/subcategorias261/organizar",data={
        "category_id":str(cats["Tabacaria"]),"subcategory_id":str(seda)
    },follow_redirects=False).status_code==404


def test_bulk_assign_and_delete_preserve_products(env):
    m,client,_,stores,cats=env
    with m.db() as conn:
        seda=conn.execute("SELECT id FROM product_subcategories261 WHERE professional_id=? AND name='Sedas'",
                         (stores[0]["id"],)).fetchone()[0]
        product=conn.execute("SELECT id FROM products WHERE professional_id=? AND name='Piteira sem filtro 448'",
                             (stores[0]["id"],)).fetchone()[0]
    response=client.post("/painel/cardapio/subcategorias261/organizar",data={
        "category_id":str(cats["Tabacaria"]),"subcategory_id":str(seda),"product_ids":str(product)
    },follow_redirects=False)
    assert response.status_code==303
    with m.db() as conn:
        assert conn.execute("SELECT subcategory_id261 FROM products WHERE id=?",(product,)).fetchone()[0]==seda
    response=client.post(f"/painel/cardapio/subcategorias261/{seda}/excluir",follow_redirects=False)
    assert response.status_code==303
    with m.db() as conn:
        assert conn.execute("SELECT subcategory_id261 FROM products WHERE id=?",(product,)).fetchone()[0]==0
        assert conn.execute("SELECT id FROM products WHERE id=?",(product,)).fetchone() is not None
    m.init_db()  # migration must be re-runnable

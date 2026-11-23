"""V451: one group photo, optional item photos, distinct order lines and prices."""
import importlib
import io
from datetime import datetime,timedelta,timezone
from pathlib import Path

import pytest
from PIL import Image
from fastapi.testclient import TestClient
from fastapi import HTTPException


def png():
    out=io.BytesIO()
    Image.new("RGB",(80,80),(94,39,155)).save(out,format="PNG")
    return out.getvalue()


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    folder=tmp_path_factory.mktemp("group451")
    m=importlib.import_module("app")
    import cms,admin_customization,email_verification
    patch=pytest.MonkeyPatch()
    patch.setenv("NOWUP_DB_ENGINE","sqlite")
    patch.setenv("NOWUP_ADMIN_EMAIL","group451@example.invalid")
    patch.setenv("NOWUP_ADMIN_PASSWORD","isolated-group451-password")
    path=folder/"catalog.sqlite"
    uploads=folder/"images";uploads.mkdir(exist_ok=True)
    for module in (m,cms,admin_customization,email_verification):
        patch.setattr(module,"DB_PATH",path)
    patch.setattr(m,"UPLOAD_DIR",uploads)
    patch.setattr(cms,"UPLOAD_DIR",uploads)
    for startup in m.app.router.on_startup:
        if startup.__name__!="start":
            startup()
    with m.db() as conn:
        stores=conn.execute("SELECT id,user_id,slug FROM professionals ORDER BY id LIMIT 2").fetchall()
        assert len(stores)==2
        for index,p in enumerate(stores):
            conn.execute("UPDATE professionals SET is_premium=1,plan_active='completo',offer_mode='menu',allows_pickup=1 WHERE id=?",(p["id"],))
            conn.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",
                         (f"group451-{index}",p["user_id"],
                          (datetime.now(timezone.utc)+timedelta(days=2)).isoformat()))
            conn.execute("INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",
                         (p["id"],"Doces",10,1,m.now_iso()))
        conn.commit()
    client=TestClient(m.app,headers={"Origin":"http://testserver"})
    client.cookies.set("nowup_session","group451-0")
    other=TestClient(m.app,headers={"Origin":"http://testserver"})
    other.cookies.set("nowup_session","group451-1")
    yield m,client,other,stores
    client.close();other.close();patch.undo()


def test_create_cover_then_add_items_with_optional_images(env):
    m,client,_,stores=env
    fail=client.post("/painel/cardapio/agrupadores",
        data={"name":"Balas Fini","category":"Doces"},follow_redirects=False)
    assert fail.status_code==400
    created=client.post("/painel/cardapio/agrupadores",
        data={"name":"Balas Fini","category":"Doces"},
        files={"photo":("capa.png",png(),"image/png")},follow_redirects=False)
    assert created.status_code==303
    assert "grupo260=" in created.headers["location"]
    with m.db() as conn:
        parent=conn.execute("SELECT * FROM products WHERE professional_id=? AND is_group_header260=1",(stores[0]["id"],)).fetchone()
        assert parent and parent["image_filename"]
        assert parent["category"]=="Doces"
        assert conn.execute("SELECT COUNT(*) FROM products WHERE group_parent_id260=?",(parent["id"],)).fetchone()[0]==0
    # No child is purchasable yet, so an empty group doesn't appear on the menu.
    menu=client.get(f"/p/{stores[0]['slug']}/menu")
    assert 'data-group260="1"' not in menu.text
    no_photo=client.post(f"/painel/cardapio/agrupadores/{parent['id']}/itens",
        data={"name":"Fini Morango","price":"5,50","available":"1"},follow_redirects=False)
    assert no_photo.status_code==303
    with_photo=client.post(f"/painel/cardapio/agrupadores/{parent['id']}/itens",
        data={"name":"Fini Uva","price":"6,20","available":"1"},
        files={"photo":("uva.png",png(),"image/png")},follow_redirects=False)
    assert with_photo.status_code==303
    with m.db() as conn:
        children=conn.execute("SELECT * FROM products WHERE group_parent_id260=? ORDER BY id",(parent["id"],)).fetchall()
        assert len(children)==2
        assert children[0]["name"]=="Fini Morango" and children[0]["image_filename"]==""
        assert children[1]["name"]=="Fini Uva" and children[1]["image_filename"]
        assert children[0]["category"]==children[1]["category"]=="Doces"
        assert children[0]["price_cents"]==550 and children[1]["price_cents"]==620
    menu=client.get(f"/p/{stores[0]['slug']}/menu")
    assert menu.status_code==200
    assert menu.text.count('data-group260="1"')==1
    assert 'Fini Morango' in menu.text and 'Fini Uva' in menu.text
    assert f'data-group-photo260="/uploads/{parent["image_filename"]}"' in menu.text
    assert f'data-group-photo260="/uploads/{children[1]["image_filename"]}"' in menu.text
    assert "Escolher entre 2 opções" in menu.text
    assert 'data-id="'+str(parent["id"])+'"' in menu.text
    panel=client.get("/painel")
    assert panel.status_code==200
    assert "Foto do produto (opcional)" in panel.text
    assert "Adicionar produto" in panel.text


def test_validation_rejects_group_header_and_hidden_cover(env):
    m,client,other,stores=env
    from nowup_storeapp257 import validate
    with m.db() as conn:
        parent=conn.execute("SELECT * FROM products WHERE professional_id=? AND is_group_header260=1",(stores[0]["id"],)).fetchone()
        child=conn.execute("SELECT * FROM products WHERE professional_id=? AND group_parent_id260=? ORDER BY id",(stores[0]["id"],parent["id"])).fetchone()
        store=conn.execute("SELECT * FROM professionals WHERE id=?",(stores[0]["id"],)).fetchone()
        g=dict(vars(m));g["shop_status"]=lambda _:{"open":True}
        with pytest.raises(HTTPException) as exc:
            validate(g,conn,store,'[{"id":'+str(parent["id"])+',"quantity":1}]',"pickup","pix","","","","",stock_only391=True)
        assert exc.value.status_code==400
        order=validate(g,conn,store,'[{"id":'+str(child["id"])+',"quantity":1}]',"pickup","pix","","","","",stock_only391=True)
        line=order[0][0]
        assert line[0]["name"]=="Balas Fini — Fini Morango"
        assert line[0]["image_filename"]==parent["image_filename"]
        assert line[4]==550
        conn.execute("UPDATE products SET available=0 WHERE id=?",(parent["id"],))
        with pytest.raises(HTTPException) as exc:
            validate(g,conn,store,'[{"id":'+str(child["id"])+',"quantity":1}]',"pickup","pix","","","","",stock_only391=True)
        assert exc.value.status_code==409
        conn.execute("UPDATE products SET available=1 WHERE id=?",(parent["id"],))
        conn.commit()
    forbidden=other.post(f"/painel/cardapio/agrupadores/{parent['id']}/itens",
        data={"name":"Outro","price":"1,00","available":"1"},follow_redirects=False)
    assert forbidden.status_code==404


def test_edit_individual_photo_remains_optional(env):
    m,client,_,stores=env
    with m.db() as conn:
        parent=conn.execute("SELECT id,image_filename FROM products WHERE professional_id=? AND is_group_header260=1",(stores[0]["id"],)).fetchone()
        child=conn.execute("SELECT id FROM products WHERE group_parent_id260=? AND name='Fini Morango'",(parent["id"],)).fetchone()
    change=client.post(f"/painel/cardapio/agrupadores/{parent['id']}/itens/{child['id']}",
        data={"name":"Fini Morango","price":"5,90","available":"1"},
        files={"photo":("morango.png",png(),"image/png")},follow_redirects=False)
    assert change.status_code==303
    with m.db() as conn:
        latest=conn.execute("SELECT price_cents,image_filename FROM products WHERE id=?",(child["id"],)).fetchone()
        assert latest["price_cents"]==590 and latest["image_filename"] and latest["image_filename"]!=parent["image_filename"]

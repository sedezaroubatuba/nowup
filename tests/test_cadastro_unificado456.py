"""V456: keep existing catalog behavior while refreshing presentation and optional margins."""
from test_merchant228 import env
from nowup_combos303 import current_price
import nowup_costs413


def store_product(m, client, store, name, price="10,00", barcode=""):
    result = client.post("/painel/cardapio/produtos", data={
        "name": name, "category": "Geral", "price": price,
        "barcode456": barcode, "available": "1", "extras_mode": "none",
    }, follow_redirects=False)
    assert result.status_code == 303
    with m.db() as conn:
        product = conn.execute("SELECT * FROM products WHERE professional_id=? AND name=? ORDER BY id DESC LIMIT 1",
                               (store,name)).fetchone()
        assert product
        return product["id"]


def test_optional_cost_without_activation_and_saved_barcode(env):
    m,client,_,store,_=env
    with m.db() as conn:
        enabled=conn.execute("SELECT enabled FROM cost_settings413 WHERE professional_id=?",(store,)).fetchone()
        assert not enabled or enabled["enabled"] == 0
    result=client.post("/painel/cardapio/produtos",data={
        "name":"V456 com custo", "category":"Geral", "price":"10,00",
        "barcode456":"7891234567890", "cost_price413":"7,00",
        "available":"1","extras_mode":"none"
    },follow_redirects=False)
    assert result.status_code==303
    with m.db() as conn:
        row=conn.execute("SELECT * FROM products WHERE professional_id=? AND name='V456 com custo'",(store,)).fetchone()
        assert row and row["barcode456"]=="7891234567890"
        exact=nowup_costs413.effective_cost(conn,store,row["id"])
        assert exact=={"cents":700,"estimated":False}
    result=client.post(f"/painel/cardapio/produtos/{row['id']}",data={
        "name":"V456 com custo", "category":"Geral", "price":"12,00",
        "barcode456":"","cost_price413":"","cost_present456":"1","available":"1","extras_mode":"none"
    },follow_redirects=False)
    assert result.status_code==303
    with m.db() as conn:
        saved=conn.execute("SELECT * FROM products WHERE id=?",(row["id"],)).fetchone()
        assert saved["barcode456"]==""
        estimated=nowup_costs413.effective_cost(conn,store,row["id"])
        assert estimated["estimated"] is True
        assert estimated["cents"]==960  # Illustrative 20% margin => cost 80% of sale.


def test_blank_selling_price_is_unavailable_draft(env):
    m,client,_,store,_=env
    response=client.post("/painel/cardapio/produtos",data={
        "name":"V456 preço pendente","category":"Geral","price":"",
        "available":"1","extras_mode":"none"
    },follow_redirects=False)
    assert response.status_code==303
    with m.db() as conn:
        row=conn.execute("SELECT price_cents,available FROM products WHERE professional_id=? AND name=?",
                         (store,"V456 preço pendente")).fetchone()
        assert row["price_cents"]==0
        assert row["available"]==0


def test_unified_editor_form_and_preserved_legacy_controls(env):
    m,client,_,store,_=env
    pid=store_product(m,client,store,"V456 todas opcoes","8,50","123456")
    html=client.get("/painel").text
    assert "product-unified456.css" in html
    assert "product-editor410.js?v=456" in html
    assert "Produtos e Cadastro" in html and "Produtos e Histórico" in html
    assert "name=\"recommend256\"" in html
    assert "id=\"cadastrar-combo\"" in html
    assert "id=\"novo-lanche322\"" in html
    assert "id=\"produtos-peso370\"" in html
    assert f'data-barcode456="123456"' in html
    row=client.get("/painel/todos-produtos")
    assert row.status_code==200
    assert "all-products455.js?v=456" in row.text


def test_sales_history_cost_estimate_separate(env):
    m,client,_,store,_=env
    cost=store_product(m,client,store,"V456 produto sem custo","10,00")
    with m.db() as conn:
        result=nowup_costs413.effective_cost(conn,store,cost)
        assert result["cents"]==800 and result["estimated"]
    response=client.get("/painel/todos-produtos?q=V456%20produto%20sem%20custo")
    assert response.status_code==200
    assert "Estimativa com margem de 20%" in response.text

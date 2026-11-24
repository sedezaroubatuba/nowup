"""V460 bulk safety: 20 max, one transaction, no cross-shop edits or history resets."""
import json

import pytest
from test_merchant228 import env


@pytest.fixture(scope="module")
def batch_env(env):
    m, client, _, store, other = env
    with m.db() as conn:
        for category in ("Bebidas460", "Tabacaria460"):
            conn.execute(
                "INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)",
                (store, category, 2, 1, m.now_iso()))
        ids=[]
        for i in range(21):
            name="Lote460 "+str(i).zfill(2)
            product=conn.execute("""INSERT INTO products(professional_id,name,category,price_cents,available,created_at,updated_at)
              VALUES(?,?,?,?,?,?,?)""",
              (store,name,"Bebidas460",1000+i*100,1,m.now_iso(),m.now_iso()))
            ids.append(product.lastrowid)
        target=conn.execute("""INSERT INTO products(professional_id,name,category,price_cents,available,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?)""",
          (store,"Gelo de coco460","Tabacaria460",700,1,m.now_iso(),m.now_iso())).lastrowid
        foreign=conn.execute("""INSERT INTO products(professional_id,name,category,price_cents,available,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?)""",
          (other,"Produto de outra loja460","Bebidas460",700,1,m.now_iso(),m.now_iso())).lastrowid
        conn.commit()
    return m,client,store,ids,target,foreign


def submit(client, ids, action, **fields):
    data={"selected_ids":[str(i) for i in ids],"operation":action}
    data.update({key:str(value) for key,value in fields.items()})
    return client.post("/painel/todos-produtos/lote",data=data,follow_redirects=False)


def test_history_page_contains_batch_selector_and_merchant_search(batch_env):
    _,client,_,ids,_,foreign=batch_env
    response=client.get("/painel/todos-produtos")
    assert response.status_code==200
    assert 'data-bulk-form460' in response.text
    assert 'data-bulk-search460' in response.text
    assert 'product-bulk460.js' in response.text
    assert 'product-bulk460.css' in response.text
    assert "Lote460 00" in response.text
    assert "Produto de outra loja460" not in response.text


def test_batch_rejects_larger_or_duplicate_selections(batch_env):
    m,client,store,ids,_,_=batch_env
    over=submit(client,ids[:21],"availability",available_value="0")
    assert over.status_code==400
    repeated=submit(client,[ids[0],ids[0]],"availability",available_value="0")
    assert repeated.status_code==400
    with m.db() as conn:
        assert all(conn.execute("SELECT available FROM products WHERE id=?",(pid,)).fetchone()[0]==1 for pid in ids[:21])



def test_related_bulk_preserves_prior_suggestions_and_writes_audit(batch_env):
    m,client,store,ids,target,_=batch_env
    prior=ids[12]
    with m.db() as conn:
        conn.execute("UPDATE products SET related256=? WHERE id=?",(str(prior),ids[0]))
        conn.commit()
    response=submit(client,ids[:2],"related",target_id=target)
    assert response.status_code==303
    assert "changed=2" in response.headers["location"]
    with m.db() as conn:
        first=conn.execute("SELECT related256 FROM products WHERE id=?",(ids[0],)).fetchone()[0]
        second=conn.execute("SELECT related256 FROM products WHERE id=?",(ids[1],)).fetchone()[0]
        count=conn.execute("SELECT COUNT(*) FROM product_audit455 WHERE professional_id=? AND product_id IN (?,?)",
                           (store,ids[0],ids[1])).fetchone()[0]
    assert first==str(prior)+","+str(target)
    assert second==str(target)
    assert count==2
    response=submit(client,ids[:2],"related",target_id=target)
    assert response.status_code==303 and "changed=0" in response.headers["location"]


def test_category_change_applies_to_exact_selection(batch_env):
    m,client,store,ids,_,_=batch_env
    response=submit(client,ids[2:5],"category",new_category="Tabacaria460",subcategory_id261=0)
    assert response.status_code==303
    with m.db() as conn:
        cats=[conn.execute("SELECT category FROM products WHERE id=?",(pid,)).fetchone()[0] for pid in ids[1:6]]
    assert cats==["Bebidas460","Tabacaria460","Tabacaria460","Tabacaria460","Bebidas460"]


def test_price_batch_is_individual_and_all_or_nothing(batch_env):
    m,client,store,ids,_,_=batch_env
    first,second=ids[5:7]
    with m.db() as conn:
        old0=conn.execute("SELECT price_cents FROM products WHERE id=?",(first,)).fetchone()[0]
        old1=conn.execute("SELECT price_cents FROM products WHERE id=?",(second,)).fetchone()[0]
        conn.execute("UPDATE products SET promo_price_cents=? WHERE id=?",(old1-100,second))
        conn.commit()
    invalid=submit(client,[first,second],"prices",prices_json=json.dumps({str(first):"32,50",str(second):"1,00"}))
    assert invalid.status_code==400
    with m.db() as conn:
        assert conn.execute("SELECT price_cents FROM products WHERE id=?",(first,)).fetchone()[0]==old0
        assert conn.execute("SELECT price_cents FROM products WHERE id=?",(second,)).fetchone()[0]==old1
    good=submit(client,[first,second],"prices",prices_json=json.dumps({str(first):"32,50",str(second):"23,90"}))
    assert good.status_code==303
    with m.db() as conn:
        assert conn.execute("SELECT price_cents FROM products WHERE id=?",(first,)).fetchone()[0]==3250
        assert conn.execute("SELECT price_cents FROM products WHERE id=?",(second,)).fetchone()[0]==2390
        assert conn.execute("SELECT COUNT(*) FROM product_audit455 WHERE product_id IN (?,?)",(first,second)).fetchone()[0]>=2


def test_cross_store_id_aborts_whole_batch(batch_env):
    m,client,store,ids,target,foreign=batch_env
    pid=ids[7]
    before=m.db()
    try:previous=before.execute("SELECT available FROM products WHERE id=?",(pid,)).fetchone()[0]
    finally:before.close()
    response=submit(client,[pid,foreign],"availability",available_value="0")
    assert response.status_code==404
    with m.db() as conn:
        assert conn.execute("SELECT available FROM products WHERE id=?",(pid,)).fetchone()[0]==previous
        assert conn.execute("SELECT available FROM products WHERE id=?",(foreign,)).fetchone()[0]==1


def test_group_member_prevents_moving_category_of_entire_batch(batch_env):
    m,client,store,ids,_,_=batch_env
    with m.db() as conn:
        cover=conn.execute("""INSERT INTO products(professional_id,name,category,price_cents,is_group_header260,available,created_at,updated_at)
          VALUES(?,?,?,0,1,1,?,?)""",(store,"Capa460","Bebidas460",m.now_iso(),m.now_iso())).lastrowid
        member=conn.execute("""INSERT INTO products(professional_id,name,category,price_cents,group_parent_id260,available,created_at,updated_at)
          VALUES(?,?,?,?,?,1,?,?)""",(store,"Sabor460","Bebidas460",1200,cover,m.now_iso(),m.now_iso())).lastrowid
        conn.commit()
    response=submit(client,[ids[8],member],"category",new_category="Tabacaria460")
    assert response.status_code==400
    with m.db() as conn:
        assert conn.execute("SELECT category FROM products WHERE id=?",(ids[8],)).fetchone()[0]=="Bebidas460"
        assert conn.execute("SELECT group_parent_id260 FROM products WHERE id=?",(member,)).fetchone()[0]==cover


def test_batch_does_not_change_sales_or_order_items(batch_env):
    m,client,store,ids,target,_=batch_env
    with m.db() as conn:
        before=conn.execute("SELECT COUNT(*) FROM orders WHERE professional_id=?",(store,)).fetchone()[0]
        lines=conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
    response=submit(client,[ids[9]],"availability",available_value="0")
    assert response.status_code==303
    with m.db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM orders WHERE professional_id=?",(store,)).fetchone()[0]==before
        assert conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]==lines


def test_batch_accepts_twenty_products(batch_env):
    m,client,_,ids,_,_=batch_env
    with m.db() as conn:
        conn.executemany("UPDATE products SET available=1 WHERE id=?", [(pid,) for pid in ids[:20]])
        conn.commit()
    accepted=submit(client,ids[:20],"availability",available_value="0")
    assert accepted.status_code==303
    assert "changed=20" in accepted.headers["location"]

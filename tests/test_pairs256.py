from test_merchant228 import env
from fastapi import HTTPException
from nowup_pairs256 import validate_pairs
import pytest

def test_pairs_save_scope_render_and_clear(env):
    m,client,_,pid,other=env
    with m.db() as c:
        ids=[]
        for owner,name in [(pid,'Gelo'),(pid,'Combo teste'),(other,'Outra loja')]:
            ids.append(c.execute('INSERT INTO products(professional_id,name,description,category,price_cents,available,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(owner,name,'','Geral',2000,1,m.now_iso(),m.now_iso())).lastrowid)
        c.commit()
        assert validate_pairs(c,pid,[ids[0],ids[0]])==str(ids[0])
        for invalid in [[ids[2]],[ids[1]]]:
            with pytest.raises(HTTPException):validate_pairs(c,pid,invalid,ids[1])
    form={'name':'Combo teste','price':'20,00','promo_price':'15,00','available':'1','is_combo256':'1','recommend256':'1','related256':str(ids[0])}
    response=client.post('/painel/cardapio/produtos/'+str(ids[1]),data=form,follow_redirects=False)
    assert response.status_code==303,response.text
    with m.db() as c:
        row=c.execute('SELECT * FROM products WHERE id=?',(ids[1],)).fetchone()
        assert row['related256']==str(ids[0]) and row['is_combo256']==1 and row['recommend256']==1
        slug=c.execute('SELECT slug FROM professionals WHERE id=?',(pid,)).fetchone()['slug']
    panel=client.get('/painel');assert panel.status_code==200 and 'Combos e Leve junto' in panel.text
    page=client.get('/p/'+slug+'/menu');assert page.status_code==200 and 'data-combo256="1"' in page.text and '/static/pairs256.js' in page.text
    form['related256']=str(ids[2]);assert client.post('/painel/cardapio/produtos/'+str(ids[1]),data=form,follow_redirects=False).status_code==400
    for name in ['is_combo256','recommend256','related256']:form.pop(name)
    assert client.post('/painel/cardapio/produtos/'+str(ids[1]),data=form,follow_redirects=False).status_code==303
    with m.db() as c:
        row=c.execute('SELECT * FROM products WHERE id=?',(ids[1],)).fetchone()
        assert row['related256']=='' and row['is_combo256']==0 and row['recommend256']==0

def test_builtin_combo_category_and_regular_promotion(env):
    m,client,_,pid,_=env
    for name,category,promo,expected_combo,expected_category in [('Combo direto','__combos256','',1,'Combos'),('Oferta cerveja','Cervejas','8,00',0,'Cervejas')]:
        response=client.post('/painel/cardapio/produtos',data={'name':name,'category':category,'price':'10,00','promo_price':promo,'available':'1'},follow_redirects=False)
        assert response.status_code==303,response.text
        with m.db() as c:
            product=c.execute('SELECT * FROM products WHERE professional_id=? AND name=? ORDER BY id DESC LIMIT 1',(pid,name)).fetchone()
            assert product['is_combo256']==expected_combo and product['category']==expected_category
            if promo:assert product['promo_price_cents']==800
    panel=client.get('/painel');assert panel.status_code==200
    assert 'Combos — categoria do aplicativo' in panel.text

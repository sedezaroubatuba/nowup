import json
from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order

def test_receipt_confirmation_payment_and_access(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:m.nowup_notinha401.initialize(c)
    path='/pedidos/'+str(o['id'])+'/notinha'
    page=client.get(path);assert page.status_code==200 and 'Notinha de conferência' in page.text
    assert not BeautifulSoup(page.text,'html.parser').select('[data-print401]')
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    assert client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},follow_redirects=False).status_code==303
    page=client.get(path);assert page.status_code==200 and 'Recebimento do Pix a conferir' in page.text
    assert 'Enviar notinha no WhatsApp' in page.text and 'Imprimir para o motoboy' in page.text
    assert client.post('/painel/pedidos/'+str(o['id'])+'/conferir-pix',follow_redirects=False).status_code==303
    page=client.get(path);assert 'Pix recebido e conferido pelo lojista' in page.text
    with m.db() as c:
        assert c.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND title='Atualização do pedido'",(buyer['id'],)).fetchone()[0]==1
        c.execute('UPDATE orders SET total_cents=total_cents+100 WHERE id=?',(o['id'],))
    assert 'Recebimento do Pix a conferir' in client.get(path).text
    monkeypatch.setattr(m,'current_user',lambda request:buyer)
    assert 'Enviar notinha no WhatsApp' not in client.get(path).text
    assert client.post('/painel/pedidos/'+str(o['id'])+'/conferir-pix',follow_redirects=False).status_code==403
    monkeypatch.setattr(m,'current_user',lambda request:dict(buyer,id=999999))
    assert client.get(path).status_code==404
    monkeypatch.setattr(m,'current_user',lambda request:None)
    assert client.get(path).status_code==403

def test_combo_details_preserved_no_double_charge(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    pack={'items':[{'name':'X-bacon','quantity':2},{'name':'Coca 2 L','quantity':1}],
          'units364':[{'name':'X-bacon','position':1,'notes':'Sem cebola','options':[{'name':'Bacon','price_cents':400}]},{'name':'X-bacon','position':2,'notes':'Completo','options':[]}], 'note':'Separar os lanches'}
    with m.db() as c:
        m.nowup_notinha401.initialize(c)
        c.execute('UPDATE order_items SET combo_pack305=? WHERE id=?',(json.dumps(pack),item['id']))
    path='/p/'+channel[2]+'/pedidos/'+str(o['id'])+'/notinha'
    text=BeautifulSoup(client.get(path).text,'html.parser').select_one('.nu401-paper').text
    assert 'X-bacon 1: Sem cebola' in text and 'X-bacon 2: Completo' in text
    assert 'Bacon — R$ 4,00 (já incluído)' in text and 'TOTAL: R$ 3,00' in text
    assert client.get('/p/outra-loja/pedidos/'+str(o['id'])+'/notinha').status_code==404

def test_real_store_cookie_stays_inside_store(channel,monkeypatch):
    import ast
    from pathlib import Path
    from datetime import datetime,timedelta,timezone
    m,client,result,o,item,owner,buyer=setup_order(channel)
    # Exercise the real session reader, not the fixture's fake current_user.
    tree=ast.parse(Path(m.__file__).read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='current_user')
    scope={};exec(compile(ast.Module(body=[node],type_ignores=[]),m.__file__,'exec'),m.__dict__,scope)
    monkeypatch.setattr(m,'current_user',scope['current_user'])
    pid=channel[3];slug=channel[2]
    with m.db() as c:
        c.execute('UPDATE users SET customer_store345=?,email_verified=1 WHERE id=?',(pid,buyer['id']))
        c.execute('INSERT INTO sessions(token,user_id,expires_at,store_id345) VALUES(?,?,?,?)',('receipt-cookie401',buyer['id'],(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),pid))
    client.cookies.set('nowup_loja345_'+str(pid),'receipt-cookie401',path='/p/'+slug)
    path='/p/'+slug+'/pedidos/'+str(o['id'])+'/notinha'
    r=client.get(path);assert r.status_code==200,r.text
    assert 'href="/p/'+slug+'/pedido/' in r.text
    assert client.get('/pedidos/'+str(o['id'])+'/notinha').status_code==403


def test_delivery_card_and_cash_instructions(channel):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:
        m.nowup_notinha401.initialize(c)
        for method,change,expected in [('credit',0,'LEVAR MAQUININHA'),('debit',0,'LEVAR MAQUININHA'),('cash',0,'Sem troco.'),('cash',10000,'Troco: R$ 97,00')]:
            c.execute("UPDATE orders SET payment_method=?,change_for_cents=?,fulfillment_type='delivery' WHERE id=?",(method,change,o['id']))
            order=c.execute('SELECT o.*,p.display_name FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE o.id=?',(o['id'],)).fetchone()
            assert expected in m.nowup_notinha401.receipt(c,order,m.ORDER_STATUS_LABELS)

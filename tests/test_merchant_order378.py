import secrets
from datetime import datetime,timedelta,timezone
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from test_merchant228 import env
from test_storeaccounts345 import setup345


def test_merchant_link_uses_owner_session_even_with_customer_cookie(setup345):
    m,(store,_),_=setup345
    token=secrets.token_urlsafe(24)
    owner_session='owner378-'+secrets.token_hex(8)
    buyer_session='buyer378-'+secrets.token_hex(8)
    with m.db() as c:
        buyer=c.execute("INSERT INTO users(role,name,email,phone,password_hash,email_verified,created_at,customer_store345,customer_email345) VALUES('customer','Cliente378',?,'12988887777','unused',1,?,?,?)",('buyer378-'+token+'@example.invalid',m.now_iso(),store['id'],'buyer378@example.invalid')).lastrowid
        expires=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',(owner_session,store['user_id'],expires))
        c.execute('INSERT INTO sessions(token,user_id,expires_at,store_id345) VALUES(?,?,?,?)',(buyer_session,buyer,expires,store['id']))
        oid=c.execute("INSERT INTO orders(professional_id,customer_id,customer_name,customer_phone,status,total_cents,subtotal_cents,fulfillment_type,payment_method,created_at,updated_at,tracking_token,order_code,order_origin) VALUES(?,?, 'Cliente378','12988887777','new',3500,3500,'pickup','pix',?,?,?,'NU-378','external')",(store['id'],buyer,m.now_iso(),m.now_iso(),token)).lastrowid
        item=c.execute("INSERT INTO order_items(order_id,product_name,quantity,unit_price_cents) VALUES(?,'Gin exemplo',1,3500)",(oid,)).lastrowid
    client=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    client.cookies.set('nowup_session',owner_session)
    client.cookies.set('nowup_loja345_'+str(store['id']),buyer_session,path='/p/'+store['slug'])
    merchant=client.get('/pedido/'+token)
    assert merchant.status_code==200
    soup=BeautifulSoup(merchant.text,'html.parser')
    assert soup.select_one('details.nu378-edit [name="price_'+str(item)+'"]')
    assert 'Editar pedido antes de confirmar' in merchant.text
    assert soup.select_one('form[action="/painel/pedidos/'+str(oid)+'/status"] button[name="status"][value="confirmed"]')
    assert 'data-pix-payment' not in merchant.text
    assert merchant.headers['referrer-policy']=='same-origin'
    assert not soup.select('[data-order-alerts], [data-more-substitute], [data-substitute]')
    assert soup.select_one('.nu379-fields [name=qty_'+str(item)+']')
    assert soup.select_one('textarea[name=message]')
    buyer_page=client.get('/p/'+store['slug']+'/pedido/'+token)
    assert buyer_page.status_code==200 and 'details class="nu378-edit"' not in buyer_page.text
    # Editing can start directly from new, before any confirmation or Pix.
    revision={'keep':str(item),'qty_'+str(item):'1','price_'+str(item):'38.00','return_to':'link'}
    client.headers.pop('origin')
    client.headers['Referer']='http://testserver/pedido/'+token
    proposal=client.post('/painel/pedidos/'+str(oid)+'/revisao',data=revision)
    assert proposal.status_code==303 and proposal.headers['location']=='/pedido/'+token
    with m.db() as c:
        order=c.execute('SELECT status,total_cents FROM orders WHERE id=?',(oid,)).fetchone()
        assert order['status']=='awaiting_approval' and order['total_cents']==3500

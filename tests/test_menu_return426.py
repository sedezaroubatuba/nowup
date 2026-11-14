from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from test_merchant228 import env
from test_storeaccounts345 import setup345


def test_whatsapp_return_keeps_store_customer_and_recovers_order_after_login(setup345):
    m,(store,other),_=setup345
    prefix='/p/'+store['slug'];token='return-whatsapp426'
    with m.db() as c:
        c.execute("UPDATE professionals SET plan_active='completo' WHERE id=?",(store['id'],))
        uid=c.execute("INSERT INTO users(role,name,email,phone,password_hash,email_verified,created_at,customer_store345,customer_email345) VALUES('customer','Cliente Retorno','return426-internal@example.invalid','12999998888',?,1,?,?,?)",(m.hash_password('return426-password'),m.now_iso(),store['id'],'return426@example.invalid')).lastrowid
        c.execute("INSERT INTO orders(professional_id,customer_id,customer_name,customer_phone,status,total_cents,subtotal_cents,created_at,updated_at,tracking_token,order_code,order_origin,payment_method,fulfillment_type) VALUES(?,?,?,'12999998888','confirmed',500,500,?,?,?,'NU-RETURN426','external','cash','pickup')",(store['id'],uid,'Cliente Retorno',m.now_iso(),m.now_iso(),token))
    client=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    response=client.get(prefix+'/cardapio')
    assert response.status_code==200,(response.status_code,dict(response.headers),response.text[:500])
    anonymous=BeautifulSoup(response.text,'html.parser')
    assert anonymous.select_one('#store-app256')
    assert not anonymous.select_one('.mobile-bottom-nav')
    assert '"whatsappCheckout": true' in str(anonymous)
    credentials={'email':'return426@example.invalid','password':'return426-password'}
    assert client.post(prefix+'/entrar',data=credentials).headers['location']==prefix+'/cardapio'
    page=client.get('/pedido/'+token+'?lojista=1',follow_redirects=True)
    assert page.status_code==200 and page.url.path==prefix+'/pedido/'+token
    assert 'Você é o lojista de' not in page.text and 'Cliente Retorno' in page.text
    assert not BeautifulSoup(page.text,'html.parser').select('[data-status-form425]')
    assert client.get(prefix+'/sessao420').json()['authenticated'] is True
    resume=BeautifulSoup(client.get(prefix+'/cardapio').text,'html.parser').select_one('[data-store-resume426] a')
    assert resume['href']==prefix+'/pedido/'+token
    # Marketplace never acquires the store customer's identity.
    assert client.get('/sessao420').json()['authenticated'] is False
    client.post(prefix+'/sair')
    page=client.get('/pedido/'+token,follow_redirects=True)
    assert 'Você é o lojista de' not in page.text
    login=BeautifulSoup(page.text,'html.parser').select_one('a.btn.primary')['href']
    assert login==prefix+'/entrar?tipo=cliente&pedido='+token
    entry=client.get(login)
    assert client.cookies.get('nowup_customer_order426')==token,(dict(entry.headers),list(client.cookies.jar))
    assert client.post(prefix+'/entrar',data=credentials).headers['location']==prefix+'/pedido/'+token
    # Return cookies identify a destination; they never grant access to another buyer.
    client.post(prefix+'/sair');client.get(prefix+'/entrar?pedido=does-not-belong-to-this-customer')
    assert client.post(prefix+'/entrar',data=credentials).headers['location']==prefix+'/cardapio'
    assert not BeautifulSoup(client.get('/p/'+other['slug']+'/cardapio').text,'html.parser').select_one('[data-store-resume426]')

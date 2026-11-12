import base64,io,json
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from PIL import Image
import pytest
import zxingcpp
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_pix import KEY,parse


def pix_store(channel):
    m,client,slug,pid,data,product,buyer=channel
    with m.db() as c:
        c.execute('UPDATE professionals SET pix_key=?,pix_key_type=?,pix_receiver_name=?,pix_receiver_city=? WHERE id=?',(KEY,'random','Loja teste','Ubatuba',pid))
    return m,client,slug,pid,data,product,buyer


@pytest.mark.parametrize('external',[False,True])
@pytest.mark.parametrize('method',['pix','cash','debit','credit'])
def test_pix_requires_merchant_acceptance_and_other_methods_have_no_qr(channel,external,method):
    m,client,slug,pid,data,product,buyer=pix_store(channel)
    data['payment_method']=method
    endpoint='/p/'+slug+'/menu/'+('whatsapp' if external else 'pedido')
    r=client.post(endpoint,data=data,headers={'Accept':'application/json'});assert r.status_code==200,r.text
    result=r.json();page=client.get(result['redirect']);assert page.status_code==200
    node=BeautifulSoup(page.text,'html.parser').select_one('[data-pix-payment] script')
    with m.db() as c:assert c.execute('SELECT status FROM orders').fetchone()[0]=='new'
    assert node is None and 'pix' not in result
    with m.db() as c:c.execute("UPDATE orders SET status='confirmed'")
    page=client.get(result['redirect'])
    node=BeautifulSoup(page.text,'html.parser').select_one('[data-pix-payment] script')
    if method=='pix':
        assert node
        qr=json.loads(node.string);decoded=zxingcpp.read_barcode(Image.open(io.BytesIO(base64.b64decode(qr['qr_image'].split(',')[1]))))
        assert decoded.text==qr['payload'];assert parse(decoded.text)['54']=='3.00';assert parse(parse(decoded.text)['26'])['01']==KEY
        if external:
            retry=client.post(endpoint,data=data).json()
            assert retry['pix']==retry['receipt']['pix']==qr
    else:
        assert node is None and 'pix' not in result
        assert 'na entrega/retirada' in page.text or 'Dinheiro' in page.text


def test_cancelled_pix_has_refund_guidance_and_retry_cannot_replay_qr(channel):
    m,client,slug,pid,data,product,buyer=pix_store(channel)
    endpoint='/p/'+slug+'/menu/whatsapp'
    first=client.post(endpoint,data=data).json();assert not first.get('pix')
    with m.db() as c:c.execute("UPDATE orders SET status='confirmed'")
    assert client.post(endpoint,data=data).json().get('pix')
    with m.db() as c:c.execute("UPDATE orders SET status='cancelled'")
    retry=client.post(endpoint,data=data).json();assert 'pix' not in retry and 'pix' not in retry['receipt']
    page=client.get(first['redirect']);assert 'data-pix-payment' not in page.text and 'solicite a devolução do Pix' in page.text


def test_pix_cannot_be_automatically_cancelled_after_customer_could_pay(channel):
    m,client,slug,pid,data,product,buyer=pix_store(channel)
    r=client.post('/p/'+slug+'/menu/pedido',data=data,headers={'Accept':'application/json'});assert r.status_code==200
    now=datetime.now(timezone.utc)
    with m.db() as c:
        c.execute('UPDATE orders SET created_at=?',((now-timedelta(minutes=20)).isoformat(),))
        assert m.nowup_scheduling380.expire(c,now)==0
        assert c.execute('SELECT status FROM orders').fetchone()[0]=='new'


def test_cardapio_pages_do_not_render_marketplace_navigation(channel):
    m,client,slug,pid,data,product,buyer=pix_store(channel)
    with m.db() as c:c.execute("UPDATE professionals SET plan_active='cardapio' WHERE id=?",(pid,))
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data).json()
    prefix='/p/'+slug
    for path in [prefix,prefix+'/menu',prefix+'/entrar',prefix+'/cadastro',prefix+'/recuperar-senha',prefix+'/aguardando',prefix+'/termos',prefix+'/privacidade',result['redirect']]:
        r=client.get(path);assert r.status_code==200,(path,r.status_code)
        soup=BeautifulSoup(r.text,'html.parser')
        assert soup.select_one('#store-app256'),path
        assert not soup.select('header.top,#nowup-navigation,.mobile-bottom-nav,footer.footer,.rolegrid,[data-resume-carts]'),path
        for a in soup.select('a[href]'):
            url=urlsplit(a['href'])
            if url.scheme or not url.path or url.path.startswith(('/static/','/uploads/')):continue
            # Only explicit merchant entry can leave the customer storefront;
            # it still uses the central role/ownership-checked login and panel.
            if a.has_attr('data-store-merchant405'):
                assert a['href'] in ('/entrar?tipo=profissional','/painel')
                continue
            assert url.path==prefix or url.path.startswith(prefix+'/'),(path,a['href'])
    # Explicit marketplace still has its own header and navigation.
    with m.db() as c:c.execute("UPDATE professionals SET plan_active='completo' WHERE id=?",(pid,))
    marketplace=BeautifulSoup(client.get(prefix+'/menu').text,'html.parser')
    assert marketplace.select_one('header.top')


@pytest.mark.parametrize('wrong_owner',[False,True])
def test_whatsapp_merchant_login_returns_to_order_only_after_ownership_check(channel,monkeypatch,wrong_owner):
    m,client,slug,pid,data,product,buyer=pix_store(channel)
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data).json()
    assert result['merchant_url'].endswith('?lojista=1')
    monkeypatch.setattr(m,'current_user',lambda request:None)
    public=client.get(result['merchant_url'].replace('http://testserver',''))
    assert public.status_code==200 and 'Você é o lojista de' in public.text
    assert '/entrar?tipo=profissional' in public.text and 'nowup_merchant_order398' in client.cookies
    with m.db() as c:
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id'+('<>?' if wrong_owner else '=?')+' LIMIT 1',(pid,)).fetchone())
        c.execute('UPDATE users SET password_hash=?,email_verified=1 WHERE id=?',(m.hash_password('merchant398-password'),owner['id']))
    response=client.post('/entrar',data={'email':owner['email'],'password':'merchant398-password','tipo':'profissional'},follow_redirects=False)
    expected='/painel' if wrong_owner else '/pedido/'+result['redirect'].rsplit('/',1)[1]
    assert response.status_code==303 and response.headers['location']==expected,response.text
    assert 'nowup_merchant_order398' not in client.cookies


def test_accepting_revision_redirects_inside_same_store(channel,monkeypatch):
    from test_order_link377 import setup_order
    m,client,result,order,item,owner,buyer=setup_order(channel)
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    revision={'keep':str(item['id']),'qty_'+str(item['id']):'1','price_'+str(item['id']):'4.00'}
    assert client.post('/painel/pedidos/'+str(order['id'])+'/revisao',data=revision,follow_redirects=False).status_code==303
    with m.db() as c:rid=c.execute('SELECT id FROM order_revisions WHERE order_id=?',(order['id'],)).fetchone()[0]
    monkeypatch.setattr(m,'current_user',lambda request:buyer)
    response=client.post(result['redirect']+'/revisao/'+str(rid),data={'decision':'accept'},follow_redirects=False)
    assert response.status_code==303 and response.headers['location']==result['redirect']
    page=client.get(response.headers['location']);soup=BeautifulSoup(page.text,'html.parser')
    assert soup.select_one('#store-app256') and not soup.select_one('header.top')


def test_missing_pix_settings_does_not_claim_qr_is_available(channel):
    m,client,slug,pid,data,product,buyer=channel
    with m.db() as c:c.execute("UPDATE professionals SET pix_key_type='' WHERE id=?",(pid,))
    response=client.post('/p/'+slug+'/menu/whatsapp',data=data)
    assert response.status_code==200
    result=response.json();assert 'pix' not in result
    assert 'Aguardando aceite da loja' in result['receipt']['status']
    with m.db() as c:c.execute("UPDATE orders SET status='confirmed'")
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data).json()
    assert result['receipt']['status']=='Pedido enviado — solicite os dados Pix à loja'

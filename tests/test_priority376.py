"""Regression checks for the immediate audit fixes, using disposable data only."""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from datetime import datetime,timedelta,timezone
from xml.etree import ElementTree as ET
import io,json,sqlite3,zipfile
import pytest
from fastapi import HTTPException
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from nowup_public376 import contact_workbook,check_public,initialize,XMLNS


def test_export_contains_only_literal_text_cells():
    raw=['=1+1','+cmd','-1+1','@SUM(A1)','\t=HYPERLINK("https://example.invalid")','＝1+1','normal\x00<& café']
    data=contact_workbook([raw])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        cells=sheet.findall('.//{'+XMLNS+'}row')[1].findall('{'+XMLNS+'}c')
        assert [c.get('t') for c in cells]==['inlineStr']*7
        assert cells[0].find('.//{'+XMLNS+'}t').text=='=1+1'
        assert cells[-1].find('.//{'+XMLNS+'}t').text=='normal<& café'
        assert sheet.findall('.//{'+XMLNS+'}f')==[]
        assert 'vbaProject.bin' not in z.namelist()
        assert b'TargetMode="External"' not in b''.join(z.read(n) for n in z.namelist() if n.endswith('.rels'))


def rate_db(tmp_path):
    path=tmp_path/'rate.db'
    def connect():return sqlite3.connect(path,timeout=10)
    with connect() as c:initialize(c)
    return connect


def test_public_limits_persist_and_ignore_forwarded_spoofing(tmp_path):
    db=rate_db(tmp_path)
    request=SimpleNamespace(client=SimpleNamespace(host='192.0.2.1'),headers={'X-Forwarded-For':'203.0.113.1'})
    for i in range(5):
        request.headers['X-Forwarded-For']='203.0.113.'+str(i)
        check_public(db,request,now=120)
    with pytest.raises(HTTPException) as error:check_public(db,request,now=121)
    assert error.value.status_code==429 and error.value.headers['Retry-After']=='59'
    other=SimpleNamespace(client=SimpleNamespace(host='192.0.2.2'))
    check_public(db,other,now=121)
    check_public(db,request,now=180)


def test_concurrent_public_submissions_do_not_bypass_limit(tmp_path):
    db=rate_db(tmp_path);request=SimpleNamespace(client=SimpleNamespace(host='192.0.2.1'))
    def send(_):
        try:check_public(db,request,now=120);return 200
        except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=8) as pool:codes=list(pool.map(send,range(12)))
    assert codes.count(200)==5 and codes.count(429)==7


def test_contact_routes_limit_and_xlsx_authorization(checkout,monkeypatch):
    import cms
    m,client,*_=checkout;monkeypatch.setattr(cms,'db',m.db);cms.init_cms_db()
    for _ in range(5):assert client.post('/contato',data={'name':'=1+1','message':'Teste'},follow_redirects=False).status_code==303
    blocked=client.post('/noticias/1/comentar',data={'name':'Teste','comment':'Teste'},follow_redirects=False)
    assert blocked.status_code==429 and 'Retry-After' in blocked.headers
    # No unauthenticated or customer download of contact data.
    assert client.get('/admin/cms/leads.xlsx').status_code==403
    monkeypatch.setattr(cms,'allow',lambda *args:({'id':1},'admin'))
    result=client.get('/admin/cms/leads.xlsx')
    assert result.status_code==200 and result.content.startswith(b'PK')
    assert '.xlsx' in result.headers['content-disposition'] and 'no-store' in result.headers['cache-control']
    assert client.get('/admin/cms/leads.csv',follow_redirects=False).headers['location']=='/admin/cms/leads.xlsx'


def test_whatsapp_history_is_idempotent_private_and_not_a_paid_order(channel,monkeypatch):
    m,client,slug,pid,data,product,customer=channel
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data).json()
    # Current flow releases Pix on checkout; it no longer requires prior review.
    assert result['recorded'] and not result['review_required'] and not result['whatsapp_only'] and result['order_code'].startswith('NU-')
    assert client.post('/p/'+slug+'/menu/whatsapp',data=data).json()==result
    with m.db() as c:
        order=dict(c.execute('SELECT * FROM orders').fetchone())
        assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM checkout_requests229').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM push_jobs').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM notifications').fetchone()[0]>=1
        assert order['status']=='new' and order['whatsapp_opened']==0
        assert c.execute('SELECT COUNT(*) FROM orders WHERE status=\'completed\'').fetchone()[0]==0
        owner=dict(c.execute('SELECT * FROM users WHERE id=(SELECT user_id FROM professionals WHERE id=?)',(pid,)).fetchone())
    page=client.get('/p/'+slug+'/pedidos');assert result['order_code'] in page.text
    page=client.get(result['redirect']);assert 'Aguardando atendimento da loja' in page.text
    assert 'Seu pedido chegou à sala de pedidos' not in page.text
    data['notes']='changed';assert client.post('/p/'+slug+'/menu/whatsapp',data=data).status_code==409
    other=dict(customer,id=customer['id']+10000);monkeypatch.setattr(m,'current_user',lambda request:other)
    assert result['order_code'] not in client.get('/p/'+slug+'/pedidos').text
    assert 'Continuar no WhatsApp' not in client.get(result['redirect']).text
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    response=client.post('/painel/pedidos/'+str(order['id'])+'/status',data={'status':'confirmed'},follow_redirects=False)
    assert 'ok=pedido' in response.headers['location']
    with m.db() as c:assert c.execute('SELECT status FROM orders').fetchone()[0]=='confirmed'


def test_whatsapp_order_limit_rejects_excess_and_allows_retry(channel):
    m,client,slug,pid,data,product,customer=channel
    first=None
    for i in range(5):
        data['request_key']='wa-priority-376-'+str(i)
        result=client.post('/p/'+slug+'/menu/whatsapp',data=data)
        assert result.status_code==200
        if first is None:first=result.json()
    data['request_key']='wa-priority-376-5'
    assert client.post('/p/'+slug+'/menu/whatsapp',data=data).status_code==429
    data['request_key']='wa-priority-376-0'
    assert client.post('/p/'+slug+'/menu/whatsapp',data=data).json()==first


def test_whatsapp_link_order_stays_out_of_queue_and_preserves_report(channel,monkeypatch):
    m,client,slug,pid,data,*_=channel
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data).json()
    with m.db() as c:
        day=datetime.now(m.SAO_PAULO_TZ).date()
        board=m.nowup_merchant228.board(c,pid,*m.order_day_bounds(day),m.SAO_PAULO_TZ)
    assert board['active']==0
    assert not any(o['order_code']==result['order_code'] for stage in board['stages'] for o in stage['orders'])
    with m.db() as c:
        assert m.orders_for_day(c,pid,day)==[]
        owner=dict(c.execute('SELECT * FROM users WHERE id=(SELECT user_id FROM professionals WHERE id=?)',(pid,)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    alerts=client.get('/painel/pedidos/novos').json()
    assert alerts['orders']==[] and alerts['pending_count']==0 and alerts['pending_order'] is None
    import nowup_sales107
    monkeypatch.setattr(nowup_sales107,'_db',m.db)
    nowup_sales107.initialize()
    with m.db() as c:
        import nowup_reports98
        nowup_reports98.init(c)
        report=nowup_reports98.build(c,pid,day,day)
        assert report['received_channels']==[('WhatsApp',1)]
        assert report['total']==0
        c.execute("UPDATE orders SET status='completed'")
        report=nowup_reports98.build(c,pid,day,day)
        assert report['channels']==[('WhatsApp',[1,result['total_cents']])]
        from nowup_sales107 import sales_summary
        assert sales_summary(c,pid,day,day)['origins']['WhatsApp']['count']==1

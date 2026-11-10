from datetime import datetime,timedelta,timezone
import json
import pytest
from fastapi import HTTPException
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
import nowup_scheduling380 as scheduling


def test_same_day_slots_only_and_store_opt_in(checkout):
    m,*_=checkout
    now=datetime(2026,11,8,14,0,tzinfo=scheduling.TZ)
    p={'business_status':'open','business_hours':json.dumps({'sun':{'enabled':True,'start':'16:00','end':'23:00'}}),'allow_schedule380':1}
    # Use the application's actual weekday keys.
    p['business_hours']=json.dumps({m.DAYS[now.weekday()]:{'enabled':True,'start':'16:00','end':'23:00'}})
    options=scheduling.slots(p,now)
    assert options[0]['label']=='16:00' and all(x['value'].startswith('2026-11-08') for x in options)
    selected,start=scheduling.validate(p,options[0]['value'],now)
    assert datetime.fromisoformat(start).astimezone(scheduling.TZ).hour==16
    for raw in ['2026-11-09T16:00','2026-11-08T15:00','2026-11-08T23:00']:
        with pytest.raises(HTTPException):scheduling.validate(p,raw,now)
    p['allow_schedule380']=0
    assert scheduling.slots(p,now)==[]
    with pytest.raises(HTTPException):scheduling.validate(p,options[0]['value'],now)


def test_expiry_only_unanswered_marketplace_and_not_scheduled_before_open(channel):
    m,client,slug,pid,data,product,customer=channel
    data['payment_method']='cash'
    response=client.post('/p/'+slug+'/menu/pedido',data=data,headers={'Accept':'application/json'})
    assert response.status_code==200,response.text
    now=datetime.now(timezone.utc)
    with m.db() as c:
        oid=c.execute('SELECT id FROM orders').fetchone()[0]
        c.execute('UPDATE orders SET created_at=? WHERE id=?',((now-timedelta(minutes=5)).isoformat(),oid))
        c.execute('UPDATE orders SET accept_after380=? WHERE id=?',((now+timedelta(hours=2)).isoformat(),oid))
        assert scheduling.expire(c,now)==0
        c.execute("UPDATE orders SET accept_after380='',order_origin='external' WHERE id=?",(oid,))
        assert scheduling.expire(c,now)==0
        c.execute("UPDATE orders SET order_origin='nowup',status='reviewing' WHERE id=?",(oid,))
        assert scheduling.expire(c,now)==0
        c.execute("UPDATE orders SET status='new' WHERE id=?",(oid,))
        assert scheduling.expire(c,now)==1
        assert scheduling.expire(c,now)==0
        assert c.execute('SELECT status,cancellation_reason FROM orders WHERE id=?',(oid,)).fetchone()[0]=='cancelled'
        assert c.execute("SELECT COUNT(*) FROM order_status_history WHERE order_id=? AND status='cancelled'",(oid,)).fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM push_jobs WHERE order_id=?',(oid,)).fetchone()[0]==0


def test_sede_zero_hours_exception_does_not_open_other_stores(checkout):
    m,*_=checkout
    p={'business_status':'open','business_hours':json.dumps({day:{'enabled':False} for day in m.DAYS}),'slug':'samuel-dos-santos-silva','display_name':'ADEGA SEDE ZERO'}
    assert m.shop_status(p)['open']
    p['slug']='adega-sede-zero'
    assert m.shop_status(p)['open']
    p['slug']='another-store'
    assert not m.shop_status(p)['open']
    p['slug']='samuel-dos-santos-silva';p['business_status']='paused'
    assert not m.shop_status(p)['open']

@pytest.mark.parametrize('whatsapp',[False,True])
def test_closed_store_can_only_submit_opted_in_same_day_slot(channel,monkeypatch,whatsapp):
    m,client,slug,pid,data,product,customer=channel
    fixed=datetime(2026,11,8,14,0,tzinfo=scheduling.TZ)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)
    monkeypatch.setattr(scheduling,'datetime',Clock)
    monkeypatch.setattr(m,'shop_status',lambda p:{'open':False,'label':'Fechada','detail':'','code':'closed'})
    monkeypatch.setitem(scheduling.G,'shop_status',m.shop_status)
    with m.db() as c:
        c.execute('UPDATE professionals SET allow_schedule380=1,business_hours=? WHERE id=?',(json.dumps({m.DAYS[fixed.weekday()]:{'enabled':True,'start':'16:00','end':'22:00'}}),pid))
    page=client.get('/p/'+slug+'/menu?loja=1')
    assert page.status_code==200
    assert 'name="scheduled_for380" required' in page.text
    assert 'Hoje às 16:00' in page.text
    endpoint='/p/'+slug+'/menu/'+('whatsapp' if whatsapp else 'pedido')
    no_slot=client.post(endpoint,data=data,headers={'Accept':'application/json'})
    assert no_slot.status_code==409
    data['scheduled_for380']='2026-11-08T16:00'
    response=client.post(endpoint,data=data,headers={'Accept':'application/json'})
    assert response.status_code==200,response.text
    with m.db() as c:
        order=c.execute('SELECT * FROM orders').fetchone()
        assert datetime.fromisoformat(order['scheduled_for380']).astimezone(scheduling.TZ).hour==16
        assert datetime.fromisoformat(order['accept_after380']).astimezone(scheduling.TZ).hour==16
    data['scheduled_for380']='2026-11-08T17:00'
    assert client.post(endpoint,data=data,headers={'Accept':'application/json'}).status_code==409

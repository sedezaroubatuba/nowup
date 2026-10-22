"""Integration checks against an isolated database; never connect to production."""
import importlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope='module')
def env(tmp_path_factory):
    import os
    directory=tmp_path_factory.mktemp('merchant228')
    os.environ['NOWUP_DB']=str(directory/'test.db')
    os.environ['NOWUP_UPLOAD_DIR']=str(directory/'uploads')
    os.environ['NOWUP_ADMIN_EMAIL']='admin@test.invalid'
    os.environ['NOWUP_ADMIN_PASSWORD']='isolated-local-test-password'
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    m=importlib.import_module('app')
    for callback in m.app.router.on_startup:
        if callback.__name__!='start':callback()
    with m.db() as c:
        stores=c.execute('SELECT id,user_id FROM professionals ORDER BY id LIMIT 2').fetchall()
        assert len(stores)==2
        p,other=stores
        c.execute("UPDATE professionals SET display_name='Sede Zero',offer_mode='menu',is_premium=1,plan_active='ambos' WHERE id=?",(p['id'],))
        for token,uid in [('merchant-test',p['user_id']),('other-test',other['user_id'])]:
            c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',(token,uid,(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()))
        ids={}
        for name,status,days,pid in [('Ana <script>alert(1)</script>','new',0,p['id']),('Preparo','preparing',0,p['id']),('Retirada','ready',0,p['id']),('Entrega','out_for_delivery',0,p['id']),('Antigo aberto','confirmed',-2,p['id']),('Aguarda cliente','awaiting_approval',0,p['id']),('Finalizado hoje','completed',0,p['id']),('Finalizado antigo','completed',-2,p['id']),('Outra loja','new',0,other['id'])]:
            created=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()
            cur=c.execute('INSERT INTO orders(professional_id,customer_name,status,total_cents,created_at,updated_at,fulfillment_type,order_code) VALUES(?,?,?,?,?,?,?,?)',(pid,name,status,5990,created,created,'pickup' if name=='Retirada' else 'delivery',name[:8]))
            ids[name]=cur.lastrowid
            c.execute('INSERT INTO order_items(order_id,product_name,quantity,unit_price_cents) VALUES(?,?,?,?)',(cur.lastrowid,'Produto de teste',2,2995))
        c.commit()
    client=TestClient(m.app)
    client.cookies.set('nowup_session','merchant-test')
    return m,client,ids,p['id'],other['id']

def test_board_scope_dates_and_totals(env):
    m,client,ids,pid,_=env
    day=datetime.now(m.SAO_PAULO_TZ).date()
    with m.db() as c:board=m.nowup_merchant228.board(c,pid,*m.order_day_bounds(day),m.SAO_PAULO_TZ)
    names=[o['customer_name'] for s in board['stages'] for o in s['orders']]
    assert 'Antigo aberto' in names and 'Finalizado antigo' not in names and 'Outra loja' not in names
    assert board['count']==6 and board['active']==6 and board['total']==6*5990
    old=next(o for s in board['stages'] for o in s['orders'] if o['customer_name']=='Antigo aberto')
    assert old['previous_day']
    wait=next(o for s in board['stages'] for o in s['orders'] if o['status']=='awaiting_approval')
    assert not wait['next_status']

def test_render_and_escape(env):
    _,client,_,_,_=env
    response=client.get('/painel/kanban228')
    assert response.status_code==200
    assert 'private, no-store' in response.headers['cache-control']
    assert '&lt;script&gt;' in response.text and '<script>alert(1)</script>' not in response.text
    assert 'Outra loja' not in response.text
    panel=client.get('/painel')
    assert panel.status_code==200
    assert 'data-merchant228' in panel.text and '/static/merchant228.js' in panel.text
    assert 'data-enable-order-alerts' in panel.text

def test_access_control(env):
    m,_,_,_,_=env
    assert TestClient(m.app).get('/painel/kanban228').status_code==401

def test_transition_preserves_approval_and_tenant_rules(env):
    _,client,ids,_,_=env
    def change(name,status):
        return client.post('/painel/pedidos/'+str(ids[name])+'/status',data={'status':status},headers={'origin':'http://testserver'},follow_redirects=False)
    assert change('Aguarda cliente','confirmed').status_code==409
    assert change('Outra loja','confirmed').status_code==404
    assert change('Ana <script>alert(1)</script>','preparing').status_code==409
    assert change('Ana <script>alert(1)</script>','confirmed').status_code==303
    assert change('Retirada','completed').status_code==303
    assert 'pedido-encerrado' in change('Retirada','preparing').headers['location']

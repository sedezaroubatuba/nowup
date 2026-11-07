import json
from datetime import datetime,timedelta,timezone
import pytest
from test_checkout247 import checkout
import nowup_communication372 as comm
import nowup_admin227 as adm

@pytest.fixture
def communication(checkout,monkeypatch):
    m,client,*_=checkout
    monkeypatch.setenv('NOWUP_COMMUNICATION_WORKER','0')
    monkeypatch.setattr(adm,'G',dict(vars(m)));adm.initialize();monkeypatch.setattr(comm,'G',dict(vars(m)));comm.initialize()
    with m.db() as c:
        p=dict(c.execute('SELECT p.* FROM professionals p JOIN products pr ON pr.professional_id=p.id LIMIT 1').fetchone())
        c.execute('UPDATE professionals SET is_demo=0 WHERE id=?',(p['id'],))
        c.execute("UPDATE users SET email='owner@example.com',email_verified=1 WHERE id=?",(p['user_id'],))
        admin=dict(c.execute("SELECT * FROM users WHERE role='admin'").fetchone())
    comm.initialize()
    monkeypatch.setattr(adm,'G',{**vars(m),'current_user':lambda req:admin})
    return m,client,p,admin

H={'X-Nowup-Admin':'227'}

def test_baseline_does_not_invent_dates_or_retroactively_welcome(communication):
    m,client,p,_=communication
    for _ in range(2):comm.tick()
    response=client.get('/admin/super/api/communication');assert response.status_code==200,response.text
    person=next(x for x in response.json()['contacts'] if x['id']==p['id'])
    assert person['activatedAt']==person['acceptedAt']==person['contractedAt']==''
    assert not any(k.startswith('_') for k in person)
    assert response.headers['cache-control']=='private, no-store'
    assert response.json()['deliveries']==[]


def test_welcome_verification_and_duplicate_ticks(communication,monkeypatch):
    m,client,p,_=communication
    with m.db() as c:
        c.execute('DELETE FROM communication372_contacts WHERE professional_id=?',(p['id'],))
        comm.signup(c,p['id'],comm.stamp(),False)
        c.execute('UPDATE users SET email_verified=0 WHERE id=?',(p['user_id'],))
        c.commit();comm.generate(c)
        assert c.execute('SELECT COUNT(*) FROM communication372_deliveries').fetchone()[0]==0
        c.execute('UPDATE users SET email_verified=1 WHERE id=?',(p['user_id'],));c.commit()
    monkeypatch.setattr(comm.mailing,'configured',lambda:True)
    sent=[];monkeypatch.setitem(comm.G,'send_email',lambda *args:sent.append(args) or True)
    comm.tick();comm.tick()
    assert len(sent)==1
    with m.db() as c:
        assert c.execute("SELECT COUNT(*) FROM notifications WHERE title='Bem-vindo ao NowUp!'").fetchone()[0]==1
        assert c.execute("SELECT COUNT(*) FROM communication372_deliveries WHERE state='sent'").fetchone()[0]==2
        row=c.execute('SELECT * FROM communication372_contacts WHERE professional_id=?',(p['id'],)).fetchone()
        assert row['accepted_at'] and row['terms_version']


def payload(pid,**kw):
    return {'requestKey':'test-unique-request','ids':[pid],'subject':'Olá, {nome}','body':'Tutorial da {loja}.','tutorial':'https://example.com/tutorial','purpose':'service','channels':['panel'],**kw}


def test_campaign_preview_snapshot_idempotency_and_panel(communication):
    m,client,p,_=communication
    b=payload(p['id']);preview=client.post('/admin/super/api/communication/preview',headers=H,json=b)
    assert preview.status_code==200,preview.text
    assert preview.json()['recipients']==1
    for _ in range(2):
        r=client.post('/admin/super/api/communication/send',headers=H,json=b);assert r.status_code==200,r.text
    comm.tick();comm.tick()
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM communication372_campaigns').fetchone()[0]==1
        assert c.execute("SELECT COUNT(*) FROM communication372_deliveries WHERE state='sent'").fetchone()[0]==1
        assert c.execute("SELECT COUNT(*) FROM notifications WHERE link='https://example.com/tutorial'").fetchone()[0]==1


def test_scheduling_and_cancellation(communication):
    m,client,p,_=communication
    b=payload(p['id'],scheduledAt=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    r=client.post('/admin/super/api/communication/send',headers=H,json=b);assert r.status_code==200,r.text
    cid=r.json()['campaigns'][0]['id'];comm.tick()
    with m.db() as c:assert c.execute("SELECT state FROM communication372_deliveries").fetchone()[0]=='pending'
    assert client.post('/admin/super/api/communication/cancel/'+str(cid),headers=H,json={}).status_code==200
    with m.db() as c:assert c.execute("SELECT state FROM communication372_deliveries").fetchone()[0]=='cancelled'


def test_marketing_excludes_no_consent_and_rechecks_withdrawal(communication):
    m,client,p,_=communication
    b=payload(p['id'],purpose='promotion')
    assert client.post('/admin/super/api/communication/preview',headers=H,json=b).json()['recipients']==0
    assert client.post('/admin/super/api/communication/send',headers=H,json=b).status_code==400
    with m.db() as c:
        c.execute('UPDATE communication372_contacts SET marketing_allowed=1,marketing_email_hash=? WHERE professional_id=?',(comm.digest('owner@example.com'),p['id']))
    r=client.post('/admin/super/api/communication/send',headers=H,json=b);assert r.status_code==200,r.text
    with m.db() as c:c.execute('UPDATE communication372_contacts SET marketing_allowed=0 WHERE professional_id=?',(p['id'],))
    comm.tick()
    with m.db() as c:assert c.execute('SELECT state FROM communication372_deliveries').fetchone()[0]=='skipped'


def test_email_changed_or_uncertain_is_never_automatically_resent(communication,monkeypatch):
    m,client,p,_=communication
    monkeypatch.setattr(comm.mailing,'configured',lambda:True)
    sent=[];monkeypatch.setitem(comm.G,'send_email',lambda *args:sent.append(args) or False)
    assert client.post('/admin/super/api/communication/send',headers=H,json=payload(p['id'],channels=['email'])).status_code==200
    comm.tick();comm.tick();assert len(sent)==1
    with m.db() as c:assert c.execute('SELECT state FROM communication372_deliveries').fetchone()[0]=='uncertain'
    b=payload(p['id'],channels=['email'],requestKey='second-email')
    assert client.post('/admin/super/api/communication/send',headers=H,json=b).status_code==200
    with m.db() as c:c.execute("UPDATE users SET email='other@example.com' WHERE id=?",(p['user_id'],))
    comm.tick();assert len(sent)==1


def test_trial_reminders_and_paid_before_dispatch(communication,monkeypatch):
    m,client,p,_=communication;now=datetime.now(timezone.utc);end=(now.astimezone(adm.TZ).date()+timedelta(days=7)).isoformat()
    with m.db() as c:
        c.execute("UPDATE communication372_contacts SET campaign='Primeiros 100',trial_start=?,trial_end=? WHERE professional_id=?",((now.date()-timedelta(days=83)).isoformat(),end,p['id']));c.commit()
        comm.generate(c,now);comm.generate(c,now)
        assert c.execute("SELECT COUNT(*) FROM communication372_deliveries WHERE rule_key='trial7'").fetchone()[0]==2
        c.execute('UPDATE professionals SET billing_last_paid=? WHERE id=?',(now.isoformat(),p['id']));c.commit()
    comm.tick()
    with m.db() as c:assert {r[0] for r in c.execute('SELECT state FROM communication372_deliveries')}=={'skipped'}


def test_contact_edit_dates_and_does_not_change_plan(communication):
    m,client,p,_=communication
    b={'campaign':'Primeiros 100','trial_start':'2026-11-06','trial_end':'2027-02-04','contracted_at':'','contracted_cents':4990,'contract_reference':'Contrato de teste'}
    r=client.post('/admin/super/api/communication/contact/'+str(p['id']),headers=H,json=b)
    assert r.status_code==200,r.text
    person=next(x for x in r.json()['contacts'] if x['id']==p['id']);assert person['campaign']=='Primeiros 100' and person['contractedCents']==4990
    with m.db() as c:assert c.execute('SELECT plan_active FROM professionals WHERE id=?',(p['id'],)).fetchone()[0]==p['plan_active']
    b['trial_end']='2025-01-01'
    assert client.post('/admin/super/api/communication/contact/'+str(p['id']),headers=H,json=b).status_code==400


def test_authorization_csrf_and_unsafe_links(communication,monkeypatch):
    m,client,p,admin=communication
    assert client.post('/admin/super/api/communication/send',json=payload(p['id'])).status_code==403
    assert client.post('/admin/super/api/communication/preview',headers=H,json=payload(p['id'],tutorial='javascript:alert(1)')).status_code==400
    monkeypatch.setitem(adm.G,'current_user',lambda req:{'id':p['user_id'],'role':'professional'})
    assert client.get('/admin/super/api/communication').status_code==401


def test_preference_link_never_unsubscribes_on_get(communication):
    m,client,p,_=communication
    with m.db() as c:
        c.execute('UPDATE communication372_contacts SET marketing_allowed=1 WHERE professional_id=?',(p['id'],))
        token=c.execute('SELECT optout_token FROM communication372_contacts WHERE professional_id=?',(p['id'],)).fetchone()[0]
    assert client.get('/comunicacoes372/preferencias',params={'token':token}).status_code==200
    with m.db() as c:assert c.execute('SELECT marketing_allowed FROM communication372_contacts WHERE professional_id=?',(p['id'],)).fetchone()[0]==1
    assert client.post('/comunicacoes372/preferencias',data={'token':token}).status_code==200
    with m.db() as c:assert c.execute('SELECT marketing_allowed FROM communication372_contacts WHERE professional_id=?',(p['id'],)).fetchone()[0]==0


def test_real_signup_records_consent_and_terms_without_changing_activation(communication,monkeypatch):
    m,client,p,_=communication
    monkeypatch.setattr(m,'normalize_email',lambda e:e)
    monkeypatch.setattr(m,'email_service_configured',lambda:True)
    monkeypatch.setattr(m,'send_verification',lambda *args:True)
    b=dict(name='Nova loja',email='newowner@example.com',phone='12999999999',password='strong-password',password_confirm='strong-password',accept_terms='1',plan='cardapio',offer_mode='menu',city='Ubatuba',state='SP',neighborhood='Centro',address='Rua teste, 10',business_type='restaurant',marketing_email372='1')
    r=client.post('/cadastro/profissional',data=b,follow_redirects=False)
    assert r.status_code==303 and r.headers['location']=='/cadastro/aguardando',r.text
    with m.db() as c:
        row=c.execute('SELECT t.* FROM communication372_contacts t JOIN professionals p ON p.id=t.professional_id JOIN users u ON u.id=p.user_id WHERE u.email=?',(b['email'],)).fetchone()
        assert row['accepted_at'] and row['marketing_allowed']==1 and row['welcome_eligible']==1
        assert row['activated_at']==row['contracted_at']==''


def test_bulk_group_preserves_individual_contract_and_no_trial_overwrite(communication):
    m,client,p,_=communication
    with m.db() as c:c.execute("UPDATE communication372_contacts SET contracted_at='2026-11-01',trial_start='2026-10-01',trial_end='2026-12-30' WHERE professional_id=?",(p['id'],))
    r=client.post('/admin/super/api/communication/group',headers=H,json={'ids':[p['id']],'campaign':'Primeiros 100','trialStart':'','trialEnd':''})
    assert r.status_code==200,r.text
    person=next(x for x in r.json()['contacts'] if x['id']==p['id'])
    assert person['trialEnd']=='2026-12-30' and person['contractedAt']=='2026-11-01' and person['campaign']=='Primeiros 100'


def test_stale_trial_reminder_is_skipped_and_pausing_blocks_pending_welcome(communication,monkeypatch):
    m,client,p,_=communication
    now=datetime.now(timezone.utc)
    with m.db() as c:
        c.execute('UPDATE communication372_contacts SET trial_end=? WHERE professional_id=?',((now.astimezone(adm.TZ).date()+timedelta(days=7)).isoformat(),p['id']));c.commit()
        comm.generate(c,now)
        row=dict(c.execute("SELECT * FROM communication372_deliveries WHERE channel='panel'").fetchone())
        comm.deliver_one(c,row,now+timedelta(days=1))
        assert c.execute('SELECT state FROM communication372_deliveries WHERE id=?',(row['id'],)).fetchone()[0]=='skipped'
        c.execute("DELETE FROM communication372_deliveries")
        c.execute("UPDATE communication372_contacts SET trial_end='',welcome_eligible=1 WHERE professional_id=?",(p['id'],));c.commit();comm.generate(c,now)
        cfg=comm.settings(c);cfg['onboarding']=False
        c.execute('UPDATE communication372_settings SET data=? WHERE id=1',(json.dumps(cfg),));c.commit()
    comm.tick()
    with m.db() as c:assert {r[0] for r in c.execute('SELECT state FROM communication372_deliveries')}=={'skipped'}


def test_legacy_store_metadata_without_json_id_uses_entity_primary_key(communication):
    m,client,p,_=communication
    with m.db() as c:
        c.execute("INSERT INTO adm227_entities(kind,id,data) VALUES('storemeta',?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",(p['id'],json.dumps({'trialUntil':'2027-02-04'})))
        assert adm.metadata(c,'storemeta')[p['id']]['id']==p['id']
    r=client.get('/admin/super/api/communication');assert r.status_code==200,r.text
    assert next(x for x in r.json()['contacts'] if x['id']==p['id'])['trialEnd']=='2027-02-04'
    comm.tick()


def as_owner(monkeypatch,m,p):
    with m.db() as c:owner=dict(c.execute('SELECT * FROM users WHERE id=?',(p['user_id'],)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    return owner


def test_merchant_cards_only_communication_and_dismiss_is_owned(communication,monkeypatch):
    m,client,p,_=communication
    assert client.post('/admin/super/api/communication/send',headers=H,json=payload(p['id'])).status_code==200
    comm.tick();owner=as_owner(monkeypatch,m,p)
    with m.db() as c:
        c.execute("INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,'Novo pedido no NowUp','Pedido novo','/painel',?)",(owner['id'],comm.stamp()))
    response=client.get('/painel/comunicacao/cards');assert response.status_code==200,response.text
    assert 'no-store' in response.headers['cache-control']
    assert len(response.json()['notices'])==1
    nid=response.json()['notices'][0]['id']
    assert client.post(f'/painel/comunicacao/cards/{nid}/fechar').status_code==403
    assert client.post(f'/painel/comunicacao/cards/{nid}/fechar',headers={'X-Nowup-Notice':'373'}).status_code==200
    assert client.get('/painel/comunicacao/cards').json()['notices']==[]
    assert client.post(f'/painel/comunicacao/cards/{nid}/fechar',headers={'X-Nowup-Notice':'373'}).status_code==200
    with m.db() as c:assert c.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND title='Novo pedido no NowUp' AND read_at=''",(owner['id'],)).fetchone()[0]==1


def test_other_merchant_cannot_read_or_dismiss_cards(communication,monkeypatch):
    m,client,p,_=communication
    assert client.post('/admin/super/api/communication/send',headers=H,json=payload(p['id'])).status_code==200
    comm.tick()
    as_owner(monkeypatch,m,p)
    nid=client.get('/painel/comunicacao/cards').json()['notices'][0]['id']
    with m.db() as c:other=dict(c.execute("SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id<>? LIMIT 1",(p['id'],)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:other)
    assert client.get('/painel/comunicacao/cards').json()['notices']==[]
    assert client.post(f'/painel/comunicacao/cards/{nid}/fechar',headers={'X-Nowup-Notice':'373'}).status_code==404


def test_card_is_in_merchant_layout_and_text_stays_json_not_html(communication,monkeypatch):
    m,client,p,_=communication
    assert client.post('/admin/super/api/communication/send',headers=H,json=payload(p['id'],subject='<script>not executable</script>',body='<img src=x onerror=alert(1)>')).status_code==200
    comm.tick();as_owner(monkeypatch,m,p)
    page=client.get('/');assert 'id="nu373-dialog"' in page.text and 'communication-card373.js' in page.text
    assert 'nowup-notice-logo374.png' in page.text
    notice=client.get('/painel/comunicacao/cards').json()['notices'][0]
    assert notice['message']=='<img src=x onerror=alert(1)>'
    assert '<img src=x onerror=alert(1)>' not in page.text

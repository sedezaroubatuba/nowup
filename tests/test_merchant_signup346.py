import io,secrets
from datetime import datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from test_merchant228 import env

@pytest.fixture
def registration(env,monkeypatch):
    m,*_=env
    monkeypatch.setattr(m,'normalize_email',lambda value:value.strip().lower() if '@' in value else '')
    monkeypatch.setattr(m,'email_service_configured',lambda:True)
    monkeypatch.setattr(m,'send_verification',lambda *a:True)
    client=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    with m.db() as c:category=c.execute("SELECT id FROM categories WHERE slug!='outros-comercios' LIMIT 1").fetchone()[0]
    def payload(**kw):
        return dict(name='Loja cadastro346',email='signup-'+secrets.token_hex(6)+'@example.com',phone='12999998888',password='password346',password_confirm='password346',accept_terms='1',business_type='store',plan='cardapio',offer_mode='catalog',city='Ubatuba',neighborhood='Centro',address='Rua cadastro 346',state='SP',**kw)
    return m,client,payload,category


def send(client,data,**kw):return client.post('/cadastro/profissional',data=data,**kw)
def registered(m,email):
    with m.db() as c:return c.execute('SELECT p.*,u.email,u.email_verified FROM professionals p JOIN users u ON u.id=p.user_id WHERE u.email=?',(email,)).fetchone()
def files():
    out=io.BytesIO();Image.new('RGB',(32,32),'white').save(out,'JPEG')
    return {key:('fake-document.jpg',out.getvalue(),'image/jpeg') for key in ('facade','company','identity','address_proof')}
def corporate(data,category):
    return {**data,'plan':'ambos','doc_type':'CNPJ','document':'11222333000181','legal_name':'Empresa Teste','owner_name':'Responsável teste','owner_cpf':'52998224725','owner_role':'Titular','category_choice346':str(category)}

@pytest.mark.parametrize('offer',['menu','catalog'])
def test_simple_registration_needs_no_documents_and_keeps_city(registration,offer):
    m,client,payload,_=registration;data=payload();data.update(offer_mode=offer,city='São Sebastião')
    r=send(client,data);assert r.status_code==303 and r.headers['location']=='/cadastro/aguardando',r.text
    p=registered(m,data['email']);assert p and p['document']=='' and p['simple_menu346']==1
    assert p['city']=='São Sebastião' and p['offer_mode']==offer
    assert p['plan_requested']=='cardapio' and p['plan_active']=='none' and p['blocked']==1
    with m.db() as c:assert not c.execute('SELECT 1 FROM merchant_evidence257 WHERE professional_id=?',(p['id'],)).fetchone()

@pytest.mark.parametrize('kind,doc',[('CPF','52998224725'),('CNPJ','11222333000181')])
def test_optional_document_can_be_cpf_or_cnpj(registration,kind,doc):
    m,client,payload,_=registration;data=payload();data.update(doc_type=kind,document=doc)
    assert send(client,data).headers['location']=='/cadastro/aguardando'
    p=registered(m,data['email']);assert p['doc_type']==kind and p['document']==doc
    data=payload();data.update(doc_type=kind,document='123')
    assert 'erro=documento' in send(client,data).headers['location']
    assert registered(m,data['email']) is None


def test_showcase_still_requires_cnpj_and_all_documents(registration):
    m,client,payload,category=registration;data=corporate(payload(),category)
    assert send(client,data).status_code==400
    assert registered(m,data['email']) is None
    r=send(client,data,files=files());assert r.status_code==303 and r.headers['location']=='/cadastro/aguardando',r.text
    p=registered(m,data['email']);assert p['simple_menu346']==0 and p['plan_requested']=='ambos'
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM merchant_documents257 WHERE professional_id=?',(p['id'],)).fetchone()[0]==4
    wrong=corporate(payload(),category);wrong.update(doc_type='CPF',document='52998224725')
    assert send(client,wrong,files=files()).status_code==400
    wrong=corporate(payload(),category);wrong['city']='São Sebastião'
    assert 'erro=cidade_vitrine' in send(client,wrong,files=files()).headers['location']


def test_manual_segment_is_saved_without_creating_a_public_category(registration):
    m,client,payload,_=registration;data=payload();data.update(category_choice346='other',business_type='other',business_segment346='Oficina de bicicletas')
    assert send(client,data).headers['location']=='/cadastro/aguardando'
    p=registered(m,data['email']);assert p['business_segment346']=='Oficina de bicicletas'
    with m.db() as c:
        assert not c.execute("SELECT 1 FROM categories WHERE name='Oficina de bicicletas'").fetchone()
        assert c.execute('SELECT COUNT(*) FROM professional_categories WHERE professional_id=?',(p['id'],)).fetchone()[0]==1
    missing=payload();missing.update(category_choice346='other',business_type='other')
    assert 'erro=segmento' in send(client,missing).headers['location']


def test_upgrade_requires_review_without_disabling_active_menu(registration):
    m,client,payload,category=registration;data=payload()
    assert send(client,data).status_code==303
    p=registered(m,data['email'])
    with m.db() as c:
        c.execute("UPDATE professionals SET plan_active='cardapio',plan_requested='ambos',is_premium=1,blocked=0,admission_status='approved' WHERE id=?",(p['id'],))
        c.execute('UPDATE users SET email_verified=1 WHERE id=?',(p['user_id'],))
        admin=c.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        expiry=(datetime.now(timezone.utc)+timedelta(minutes=20)).isoformat()
        c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',('upgrade-admin346',admin,expiry))
        c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',('upgrade-store346',p['user_id'],expiry));c.commit()
    client.cookies.clear();client.cookies.set('nowup_session','upgrade-admin346')
    endpoint='/admin/profissionais/'+str(p['id'])+'/plano'
    assert client.post(endpoint,data={'complimentary':'1'}).status_code==400
    client.cookies.clear();client.cookies.set('nowup_session','upgrade-store346')
    page=client.get('/painel/documentos');assert page.status_code==200 and 'name="document"' in page.text
    docs=corporate(data,category)
    r=client.post('/painel/documentos',data=docs,files=files());assert r.status_code==303,r.text
    assert registered(m,data['email'])['blocked']==0
    client.cookies.clear();client.cookies.set('nowup_session','upgrade-admin346')
    assert client.post(endpoint,data={'complimentary':'1'}).status_code==400
    review='/admin/verificacao-lojistas/'+str(p['id'])
    assert client.post(review,data={'decision':'verified','reason':'Documentos de teste conferidos','checked':'1'}).status_code==303
    assert client.post(endpoint,data={'complimentary':'1'}).status_code==303
    assert registered(m,data['email'])['plan_active']=='ambos'


def test_simple_plan_can_be_approved_without_kyc(registration,monkeypatch):
    m,client,payload,_=registration;data=payload()
    assert send(client,data).headers['location']=='/cadastro/aguardando'
    p=registered(m,data['email'])
    with m.db() as c:
        c.execute('UPDATE users SET email_verified=1 WHERE id=?',(p['user_id'],))
        admin=c.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        expiry=(datetime.now(timezone.utc)+timedelta(minutes=20)).isoformat()
        c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',('approve-simple346',admin,expiry));c.commit()
    monkeypatch.setattr(m,'send_admission_notice',lambda pid:True)
    client.cookies.clear();client.cookies.set('nowup_session','approve-simple346')
    r=client.post('/admin/profissionais/'+str(p['id'])+'/analise/approved',data={'complimentary':'1'})
    assert r.status_code==303
    p=registered(m,data['email']);assert p['plan_active']=='cardapio' and p['blocked']==0 and p['admission_status']=='approved'

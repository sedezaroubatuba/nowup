import pytest
from html.parser import HTMLParser
from test_checkout247 import checkout
import nowup_marketing309 as marketing

@pytest.fixture
def customer(checkout):
 m,client,url,payload,product,actor=checkout
 with m.db() as c:c.execute("UPDATE users SET email_verified=1,phone='12999999999' WHERE id=?",(actor['id'],))
 return m,client,actor['id']

@pytest.mark.parametrize('email,whatsapp',[(False,False),(True,False),(False,True),(True,True)])
def test_independent_choices(customer,email,whatsapp):
 m,_,uid=customer
 with m.db() as c:
  marketing.save(c,uid,email,whatsapp,source='signup')
  assert marketing.preferences(c,uid)=={'email':email,'whatsapp':whatsapp}
  assert marketing.eligible(c,uid,'email') is email and marketing.eligible(c,uid,'whatsapp') is whatsapp
  events=c.execute('SELECT * FROM marketing_consent_events309 WHERE user_id=?',(uid,)).fetchall()
  assert len(events)==2 and all(r['consent_text'] and r['version']==marketing.VERSION for r in events)

def test_existing_accounts_are_not_subscribed(customer):
 m,_,uid=customer
 with m.db() as c:assert marketing.preferences(c,uid)=={'email':False,'whatsapp':False}

def test_signup_saves_options_but_waits_for_email_verification(checkout,monkeypatch):
 m,client,*_=checkout
 monkeypatch.setattr(m,'normalize_email',lambda value:value.strip().lower())
 monkeypatch.setattr(m,'email_service_configured',lambda:True)
 monkeypatch.setattr(m,'send_verification',lambda *args:True)
 base={'name':'Cliente teste','phone':'12999999999','password':'test-password-309','password_confirm':'test-password-309','accept_terms':'1','address':'Rua Teste 10','neighborhood':'Centro','city':'Ubatuba','state':'SP'}
 for i,extra in enumerate([{}, {'marketing_email309':'1'},{'marketing_whatsapp309':'1'}]):
  r=client.post('/cadastro/cliente',data={**base,'email':f'new309-{i}@example.invalid',**extra},follow_redirects=False)
  assert r.status_code==303 and r.headers['location']=='/cadastro/aguardando'
  with m.db() as c:
   uid=c.execute('SELECT id FROM users WHERE email=?',(f'new309-{i}@example.invalid',)).fetchone()[0]
   assert marketing.preferences(c,uid)=={'email':i==1,'whatsapp':i==2}
   assert not marketing.eligible(c,uid,'email') and not marketing.eligible(c,uid,'whatsapp')

def test_own_account_withdrawal_and_tenant_boundary(customer):
 m,client,uid=customer
 with m.db() as c:other=c.execute('SELECT user_id FROM professionals LIMIT 1').fetchone()[0]
 r=client.post('/cliente/comunicacoes',data={'marketing_email309':'1','marketing_whatsapp309':'1','user_id':other},follow_redirects=False)
 assert r.status_code==303
 with m.db() as c:
  assert marketing.preferences(c,uid)=={'email':True,'whatsapp':True}
  assert c.execute('SELECT COUNT(*) FROM marketing_preferences309 WHERE user_id=?',(other,)).fetchone()[0]==0
 assert client.post('/cliente/comunicacoes',data={},follow_redirects=False).status_code==303
 with m.db() as c:
  assert marketing.preferences(c,uid)=={'email':False,'whatsapp':False}
  assert c.execute('SELECT COUNT(*) FROM marketing_consent_events309 WHERE user_id=?',(uid,)).fetchone()[0]==4

def test_new_phone_requires_a_new_choice(customer):
 m,_,uid=customer
 with m.db() as c:
  marketing.save(c,uid,True,True)
  c.execute("UPDATE users SET phone='+55 (12) 99999-9999' WHERE id=?",(uid,));assert marketing.eligible(c,uid,'whatsapp')
  c.execute("UPDATE users SET phone='12988888888' WHERE id=?",(uid,));assert not marketing.eligible(c,uid,'whatsapp')
  assert marketing.eligible(c,uid,'email')
  c.execute('UPDATE users SET is_active=0 WHERE id=?',(uid,));assert not marketing.eligible(c,uid,'email')

def test_signup_controls_are_optional_and_unchecked(customer):
 _,client,_=customer
 class Inputs(HTMLParser):
  def __init__(self):super().__init__();self.inputs=[]
  def handle_starttag(self,tag,attrs):
   if tag=='input':self.inputs.append(dict(attrs))
 response=client.get('/cadastro/cliente');assert response.status_code==200
 parser=Inputs();parser.feed(response.text);fields=[i for i in parser.inputs if i.get('name','').startswith('marketing_')]
 assert len(fields)==2 and all('checked' not in i and 'required' not in i for i in fields)
 assert any(i.get('name')=='accept_terms' and 'required' in i for i in parser.inputs)

def test_permissions_and_csrf(customer,monkeypatch):
 m,client,uid=customer
 assert client.post('/cliente/comunicacoes',headers={'Origin':'https://evil.invalid'},data={'marketing_email309':'1'}).status_code==403
 monkeypatch.setattr(m,'current_user',lambda request:None);assert client.post('/cliente/comunicacoes',data={}).status_code==401
 monkeypatch.setattr(m,'current_user',lambda request:{'id':uid,'role':'professional'});assert client.post('/cliente/comunicacoes',data={}).status_code==403

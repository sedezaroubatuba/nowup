import pytest
from test_merchant228 import env
from fastapi import HTTPException
from nowup_plans339 import offers409,PLANS
from test_merchant_signup346 import registration,registered,send,corporate,files

@pytest.mark.parametrize('city,state,expected',[
 ('Ubatuba','SP',{'cardapio','completo'}),(' ubatuba ','SP',{'cardapio','completo'}),
 ('São Sebastião','SP',{'cardapio'}),('Caraguatatuba','SP',{'cardapio'}),('Ubatuba','RJ',{'cardapio'})])
def test_city_offers_and_fixed_price(city,state,expected):
    offers=offers409({'city':city,'state':state})
    assert set(offers)==expected
    assert all(price==4990 for _,price in offers.values())
    if 'completo' in offers:assert 'cortesia' in offers['completo'][0]

@pytest.mark.parametrize('plan',['completo','ambos'])
def test_outside_signup_rejects_showcase_before_collecting_documents(registration,plan):
    m,client,payload,category=registration
    data=payload();data.update(city='São Sebastião',plan=plan)
    response=send(client,data)
    assert response.status_code==303 and 'erro=cidade_vitrine' in response.headers['location']
    assert registered(m,data['email']) is None

def test_ubatuba_courtesy_keeps_both_channels_pending_approval(registration):
    m,client,payload,category=registration
    data=corporate(payload(),category);data['plan']='completo'
    assert send(client,data,files=files()).headers['location']=='/cadastro/aguardando'
    p=registered(m,data['email'])
    assert p['plan_active']=='none' and p['plan_requested']=='completo'
    assert p['admission_status']=='pending' and PLANS['completo'][1]==4990

def test_outside_plan_upgrade_is_rejected_and_current_menu_preserved(registration,monkeypatch):
    m,client,payload,category=registration
    data=payload();data['city']='Caraguatatuba'
    assert send(client,data).headers['location']=='/cadastro/aguardando'
    p=registered(m,data['email'])
    with m.db() as c:
        c.execute("UPDATE professionals SET plan_active='cardapio',plan_requested='',admission_status='approved',blocked=0,is_premium=1 WHERE id=?",(p['id'],))
        owner=dict(c.execute('SELECT * FROM users WHERE id=?',(p['user_id'],)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    for plan in ['completo','ambos']:
        response=client.post('/painel/plano',data={'plan':plan,'offer_mode':'menu'})
        assert response.status_code==400
    with m.db() as c:
        row=c.execute('SELECT plan_active,plan_requested FROM professionals WHERE id=?',(p['id'],)).fetchone()
        assert tuple(row)==('cardapio','')
        from nowup_verification257 import require_review
        with pytest.raises(HTTPException):require_review(c,p['id'],'completo')
    panel=client.get('/painel')
    from bs4 import BeautifulSoup
    options=BeautifulSoup(panel.text,'html.parser').select('#plano select[name=plan] option')
    assert [option['value'] for option in options]==['cardapio']

import pytest
from fastapi import HTTPException
from nowup_custom192 import parse_config,validate_customization


def test_optional_question_and_boolean_response():
    config=parse_config({'question333':'  Deseja guardanapos?  ','utensils':False})
    assert config['question333']=='Deseja guardanapos?'
    assert validate_customization(config,{'answer333':True},'',False)=='Deseja guardanapos?: Sim'
    assert validate_customization(config,{'answer333':False},'',False)=='Deseja guardanapos?: Não'
    for raw in [{},{'answer333':'Sim'},{'answer333':1},{'answer333':None}]:
        with pytest.raises(HTTPException):validate_customization(config,raw,'',False)
    assert validate_customization(parse_config({'utensils':False}),{},'',False)==''
    for question in [None,False,[], 'x'*201]:
        with pytest.raises(HTTPException):parse_config({'question333':question})

from test_merchant228 import env

def test_merchant_question_persists_and_reaches_storefront(env):
    import json
    m,client,_,store_id,_=env
    config={'is_meal317':True,'question333':'Deseja molho separado?','utensils':False,'notes':True}
    data={'name':'Lanche pergunta 333','category':'Lanches','price':'20,00','available':'1','personalizable':'1','extras_mode':'none','customization192':json.dumps(config)}
    response=client.post('/painel/cardapio/produtos',data=data,follow_redirects=False);assert response.status_code==303
    with m.db() as c:
        row=c.execute('SELECT * FROM products WHERE professional_id=? AND name=?',(store_id,data['name'])).fetchone()
        saved=parse_config(row['customization192']);assert saved['question333']==config['question333']
        assert validate_customization(saved,{'answer333':True},'',False)==config['question333']+': Sim'
        slug=c.execute('SELECT slug FROM professionals WHERE id=?',(store_id,)).fetchone()[0]
    assert 'Deseja molho separado?' in client.get('/p/'+slug).text
    config['question333']='Deseja guardanapos?';data['customization192']=json.dumps(config)
    assert client.post('/painel/cardapio/produtos/'+str(row['id']),data=data,follow_redirects=False).status_code==303
    with m.db() as c:
        assert parse_config(c.execute('SELECT customization192 FROM products WHERE id=?',(row['id'],)).fetchone()[0])['question333']=='Deseja guardanapos?'

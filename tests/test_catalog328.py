from test_merchant228 import env
from starlette.requests import Request


def test_return_allowlist_and_save_origin(env):
    m,client,_,store,_=env
    for target in ['novo-produto','novo-lanche322','cadastrar-combo','ingredientes320','produto-editor328-1','combo-editor328-2']:
        req=Request({'type':'http','method':'POST','path':'/','query_string':('return_to328='+target).encode(),'headers':[]})
        assert m.catalog_return328(req,'/painel?ok=produto#cardapio').headers['location']=='/painel?ok=produto#'+target
    for target in ['https://evil.invalid','//evil.invalid','pedidos-ativos','produto-editor328--1']:
        req=Request({'type':'http','method':'POST','path':'/','query_string':('return_to328='+target).encode(),'headers':[]})
        assert m.catalog_return328(req,'/painel?ok=produto#cardapio').headers['location']=='/painel?ok=produto#cardapio'
    data={'name':'Cadastro 328','category':'Geral','price':'10,00','available':'1','extras_mode':'none'}
    response=client.post('/painel/cardapio/produtos?return_to328=novo-produto',data=data,follow_redirects=False)
    assert response.status_code==303 and response.headers['location'].endswith('#novo-produto')
    response=client.post('/painel/cardapio/ingredientes320?return_to328=ingredientes320',data={'name':'Ingrediente 328','price':'0,00'},follow_redirects=False)
    assert response.status_code==303 and response.headers['location'].endswith('#ingredientes320')
    panel=client.get('/painel');assert panel.status_code==200 and 'pair-catalog328' in panel.text
    assert 'data-pair-seed328' not in panel.text  # no existing related products in this fixture

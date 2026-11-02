import json
import sqlite3
from pathlib import Path
import pytest
from fastapi import HTTPException
from nowup_custom192 import parse_config, validate_customization
from nowup_included195 import initialize, resolve
from test_merchant228 import env


def test_sides_only_combo_and_tenant_validation():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript('CREATE TABLE professionals(id INTEGER PRIMARY KEY); CREATE TABLE products(id INTEGER PRIMARY KEY,professional_id,name,available,is_combo256);')
    initialize(c)
    c.executemany('INSERT INTO products VALUES(?,?,?,?,?)',[(1,10,'Batata frita',1,0),(2,20,'Outra loja',1,0),(3,10,'Esgotado',0,0),(4,10,'Combo pronto',1,1)])
    def config(ids):return parse_config({'is_meal317':True,'included195':{'is_combo':True,'side_product_ids':ids,'side_required':True},'notes':True})
    resolved=resolve(c,10,config([1]));assert resolved['included195']['side_product_ids']==[1]
    assert resolved['groups'][0]['options']==['Batata frita']
    assert 'Batata frita' in validate_customization(resolved,{'groups':{'side195':['Batata frita']}},'',False)
    for ids in [[],[2],[3],[4],[999],[True],[1,1]]:
        with pytest.raises(HTTPException):resolve(c,10,config(ids))
    c.close()


def test_separate_registration_save_edit_render_and_preservation(env,tmp_path):
    m,client,_,pid,other=env
    normal={'name':'Refrigerante comum 322','description':'Bebida','category':'Refrigerantes','price':'12,00','available':'1','sold_cold':'1','extras_mode':'none','is_combo256':'0','customization192':json.dumps({'is_meal317':False,'notes':True})}
    r=client.post('/painel/cardapio/produtos',data=normal,follow_redirects=False)
    assert r.status_code==303 and 'ok=produto' in r.headers['location']
    with m.db() as c:
        plain=c.execute('SELECT * FROM products WHERE name=? AND professional_id=?',(normal['name'],pid)).fetchone()
        assert plain['sold_cold']==1
        c.execute('INSERT INTO ingredients320(professional_id,name,image_filename) VALUES(?,?,?)',(pid,'Queijo 322',''))
        ingredient_id=c.execute('SELECT id FROM ingredients320 WHERE name=?',('Queijo 322',)).fetchone()['id']
        c.execute("INSERT INTO shared_extras155(professional_id,name,price_cents,available) VALUES(?,?,?,?)",(pid,'Bacon 322',300,1))
        extra_id=c.execute('SELECT id FROM shared_extras155 WHERE name=?',('Bacon 322',)).fetchone()['id'];c.commit()
    config={'is_meal317':True,'notes':True,'ingredients':[{'name':'Pão','removable':False},{'name':'Queijo 322','ingredient_id320':ingredient_id,'removable':True}],'included195':{'is_combo':True,'side_product_ids':[plain['id']],'side_count':1,'side_required':True},'combo_manual':[{'name':'Guardanapo','quantity':1}]}
    meal={**normal,'name':'X-bacon separado 322','description':'Descrição completa do lanche','category':'Lanches','price':'25,00','extras_mode':'selected','extra_ids':str(extra_id),'max_choices':'3','customization192':json.dumps(config)}
    r=client.post('/painel/cardapio/produtos',data=meal,follow_redirects=False)
    assert r.status_code==303 and r.headers['location']=='/painel?ok=refeicao#lanches-refeicoes322'
    with m.db() as c:
        saved=c.execute('SELECT * FROM products WHERE name=? AND professional_id=?',(meal['name'],pid)).fetchone()
        assert saved['is_dish']==1 and saved['sold_cold']==1 and saved['is_combo256']==0
        cfg=parse_config(saved['customization192']);assert cfg['ingredients'][0]['removable'] is False
        assert cfg['included195']['side_product_ids']==[plain['id']]
        assert c.execute('SELECT count(*) FROM product_options WHERE product_id=? AND shared_extra_id=?',(saved['id'],extra_id)).fetchone()[0]==1
    page=client.get('/painel');assert page.status_code==200
    assert 'id="lanches-refeicoes322"' in page.text
    assert page.text.count('id="ingredientes320"')==1
    assert 'data-meal-editor322="1"' in page.text
    assert 'name="sold_cold"' in page.text and 'data-combo-type303' in page.text
    import os
    Path(os.environ.get('NOWUP_PANEL322_OUTPUT',str(tmp_path/'panel.html'))).write_text(page.text)
    meal['description']='Descrição atualizada'
    r=client.post('/painel/cardapio/produtos/'+str(saved['id']),data=meal,follow_redirects=False)
    assert r.status_code==303 and 'lanches-refeicoes322' in r.headers['location']
    with m.db() as c:
        edited=c.execute('SELECT * FROM products WHERE id=?',(saved['id'],)).fetchone()
        assert edited['description']=='Descrição atualizada'
        assert parse_config(edited['customization192'])['included195']['side_product_ids']==[plain['id']]

    grouped={**config,'meal_groups324':True,'meal_combo324':True,'groups':[{'id':'escolha324','name':'Escolha sua bebida','min':4,'max':4,'quantity_mode':True,'options':[plain['name']],'product_ids':[plain['id']]}]}
    meal['customization192']=json.dumps(grouped)
    response=client.post('/painel/cardapio/produtos/'+str(saved['id']),data=meal,follow_redirects=False)
    assert response.status_code==303 and 'lanches-refeicoes322' in response.headers['location']
    with m.db() as c:
        cfg=parse_config(c.execute('SELECT customization192 FROM products WHERE id=?',(saved['id'],)).fetchone()[0])
        assert cfg['meal_groups324'] and cfg['groups'][0]['max']==4 and cfg['notes']
        assert cfg['ingredients'][0]['name']=='Pão' and not cfg['ingredients'][0]['removable']

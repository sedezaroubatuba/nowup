import json
import sqlite3
import pytest
from nowup_plans339 import PLANS, admin_plans, synchronize_admin
from test_storeapp256 import shop
from test_checkout247 import checkout

def test_admin_migration_preserves_old_contract_metadata():
    c = sqlite3.connect(':memory:')
    c.execute('CREATE TABLE adm227_entities(kind TEXT,id INTEGER,data TEXT,PRIMARY KEY(kind,id))')
    c.execute('INSERT INTO adm227_entities VALUES(?,?,?)', ('plans', 1, json.dumps(dict(id='start',price=7900))))
    c.execute('INSERT INTO adm227_entities VALUES(?,?,?)', ('storemeta', 12, '{"plan":"start","price":7900}'))
    synchronize_admin(c)
    synchronize_admin(c)
    assert [json.loads(r[0]) for r in c.execute("SELECT data FROM adm227_entities WHERE kind='plans' ORDER BY id")] == admin_plans()
    assert c.execute("SELECT data FROM adm227_entities WHERE kind='storemeta'").fetchone()[0] == '{"plan":"start","price":7900}'
    assert json.loads(c.execute("SELECT data FROM adm227_entities WHERE kind='plans_archive339'").fetchone()[0])['id'] == 'start'
    assert {k:v[1] for k,v in PLANS.items()} == {'cardapio':4990,'ambos':9990,'completo':14990}

@pytest.mark.parametrize('plan', ['cardapio', 'ambos', 'completo'])
def test_both_plans_keep_menu_checkout_and_all_merchant_tools(shop, monkeypatch, plan):
    m, client, slug, pid, url, data, product = shop
    with m.db() as c:
        c.execute('UPDATE professionals SET plan_active=?,is_premium=1,is_demo=0 WHERE id=?',(plan,pid))
        owner = dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
    menu = client.get('/p/'+slug+'/menu')
    assert menu.status_code == 200
    assert client.post(url,data=data,headers={'Accept':'application/json'}).json()['confirmed']
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    m.nowup_sales107.initialize()
    panel = client.get('/painel')
    assert panel.status_code == 200
    for marker in ['Ingredientes, acompanhamentos e adicionais', 'name="plan"', 'combos', 'slides']:
        assert marker in panel.text
    assert '<option value="vitrine"' not in panel.text
    signup = client.get('/cadastro/profissional')
    assert '<option value="vitrine"' not in signup.text
    assert '49,90' in signup.text and '99,90' in signup.text
    rejected = client.post('/painel/plano',data={'plan':'vitrine','offer_mode':'services'},follow_redirects=False)
    assert 'erro=plano' in rejected.headers['location']

def test_plan_switch_reuses_store_products_and_link(shop):
    import nowup_admin227 as adm
    m, client, slug, pid, url, data, product = shop
    adm.configure(vars(m))
    adm.initialize()
    import nowup_verification257 as verification
    verification.G.update(vars(m));verification.initialize()
    with m.db() as c:
        c.execute("INSERT INTO merchant_evidence257(professional_id,legal_name,owner_name,owner_cpf,owner_role,status) VALUES(?,'Loja teste','Titular teste','52998224725','Titular','verified')",(pid,))
        before = [tuple(r) for r in c.execute('SELECT * FROM products WHERE professional_id=?',(pid,))]
        for plan in ('cardapio', 'ambos', 'completo', 'cardapio'):
            adm.update_store(c, {'permissions':['finance']}, pid, {'plan':plan}, 'Troca solicitada pelo lojista')
            p = c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone()
            assert p['slug'] == slug and p['plan_active'] == plan and p['is_premium'] == 1
            assert [tuple(r) for r in c.execute('SELECT * FROM products WHERE professional_id=?',(pid,))] == before
    assert client.get('/p/'+slug+'/menu').status_code == 200

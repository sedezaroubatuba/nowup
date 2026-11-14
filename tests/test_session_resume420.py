from fastapi.testclient import TestClient
from test_merchant228 import env
from test_storeaccounts345 import setup345,signup


def test_store_login_is_reused_on_return_and_stays_store_scoped(setup345):
    m,(a,b),sent=setup345
    client=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    assert signup(client,a,'Cliente salvo','session-resume-password').status_code==303
    with m.db() as c:
        u=c.execute('SELECT * FROM users WHERE customer_store345=?',(a['id'],)).fetchone()
        token=u['verification_token'];uid=u['id']
    client.get('/p/'+a['slug']+'/verificar-email?token='+token)
    login=client.post('/p/'+a['slug']+'/entrar',data={'email':'shared345@example.com','password':'session-resume-password'})
    assert login.status_code==303 and 'Max-Age=2592000' in login.headers['set-cookie']
    session=client.cookies.get('nowup_loja345_'+str(a['id']))
    for _ in range(3):
        state=client.get('/p/'+a['slug']+'/sessao420');assert state.status_code==200
        assert state.json()=={'authenticated':True,'role':'customer','user_id':uid}
        assert 'no-store' in state.headers['cache-control']
        page=client.get('/p/'+a['slug']+'/entrar');assert page.status_code==303 and page.headers['location']=='/p/'+a['slug']+'/cardapio'
    assert not client.get('/p/'+b['slug']+'/sessao420').json()['authenticated']
    assert not client.get('/sessao420').json()['authenticated']
    with m.db() as c:c.execute('DELETE FROM sessions WHERE token=?',(session,))
    assert not client.get('/p/'+a['slug']+'/sessao420').json()['authenticated']
    assert client.get('/p/'+a['slug']+'/entrar').status_code==200

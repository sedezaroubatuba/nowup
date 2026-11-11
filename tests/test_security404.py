from nowup_auth247 import password_matches404
from test_merchant228 import env


def test_unknown_account_still_runs_password_verification():
    calls=[]
    def verify(password, stored):
        calls.append((password,stored))
        return True
    assert not password_matches404('attempt',None,verify)
    assert len(calls)==1 and '$' in calls[0][1]
    assert password_matches404('attempt','real-hash',verify)
    assert calls[-1][1]=='real-hash'
    assert not password_matches404('x'*129,'real-hash',verify)
    assert len(calls)==2


def test_admin_entry_link_does_not_log_out_merchant(env):
    m,client,*_=env
    token=client.cookies.get('nowup_session')
    response=client.get('/admin/entrar',follow_redirects=False)
    assert response.status_code==303 and response.headers['location']=='/entrar?tipo=admin'
    assert 'set-cookie' not in response.headers
    with m.db() as c:
        assert c.execute('SELECT 1 FROM sessions WHERE token=?',(token,)).fetchone()
    assert client.get('/painel/kanban228').status_code==200

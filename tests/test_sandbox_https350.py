"""Reproduce Render TLS termination with the real isolated playground child."""
from datetime import datetime,timedelta,timezone
from fastapi.testclient import TestClient
from test_merchant228 import env
import pytest

@pytest.mark.parametrize('tls',[False,True])
def test_playground_preserves_browser_origin_without_allowing_cross_site(env,monkeypatch,tls):
    m,_,_,_,_=env
    monkeypatch.setenv('NOWUP_HTTPS','1' if tls else '0')
    monkeypatch.delenv('NOWUP_PUBLIC_ORIGIN',raising=False)
    scheme='https' if tls else 'http'
    # Browser connects over HTTPS, while the application sees plain HTTP from Render.
    async def gateway(scope,receive,send):
        if scope['type']=='http':scope={**scope,'scheme':'http'}
        await m.app(scope,receive,send)
    with m.db() as c:
        uid=c.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        token='sandbox350-'+scheme
        c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',(token,uid,(datetime.now(timezone.utc)+timedelta(minutes=20)).isoformat()))
        before=c.execute('SELECT COUNT(*) FROM professionals').fetchone()[0]
    client=TestClient(gateway,base_url=scheme+'://testserver',headers={'Origin':scheme+'://testserver'},follow_redirects=False)
    client.cookies.set('nowup_session',token)
    entered=client.post('/admin/modo-teste/entrar')
    assert entered.status_code==303,entered.text
    assert client.get('/__controle333').status_code==200
    # A spoofed forwarding header is discarded by the parent.
    response=client.post('/__loja333',data={'name':'Loja HTTPS350 '+scheme,'plan':'cardapio','offer':'menu'},headers={'X-Forwarded-Proto':'http' if tls else 'https'})
    assert response.status_code==303,response.text
    panel=client.get('/painel');assert panel.status_code==200,panel.text
    assert 'Loja HTTPS350 '+scheme in panel.text
    assert client.post('/__loja333',data={'name':'Foreign','plan':'cardapio','offer':'menu'},headers={'Origin':'https://evil.invalid','Sec-Fetch-Site':'cross-site'}).status_code==403
    assert client.post('/admin/modo-teste/sair').status_code==303
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM professionals').fetchone()[0]==before
    assert client.cookies.get('nowup_session')==token

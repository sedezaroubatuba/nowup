import pytest
from test_storeapp257 import channel
from test_storeapp256 import shop
from test_checkout247 import checkout


@pytest.mark.parametrize('number', ['(12) 98888-7777', '+55 12 98888-7777'])
def test_owner_changes_store_and_order_phone_without_admin(channel, monkeypatch, number):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
        other=dict(c.execute('SELECT id,whatsapp FROM professionals WHERE id<>? LIMIT 1',(pid,)).fetchone())
        c.execute('INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,?,?)',(pid,'5512999999999','whatsapp'))
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    response=client.post('/painel/perfil',data={'display_name':'Sede Zero','city':'Ubatuba','offer_mode':'menu','whatsapp':number},follow_redirects=False)
    assert response.status_code==303,response.text
    with m.db() as c:
        assert c.execute('SELECT whatsapp FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='12988887777'
        dest=c.execute('SELECT whatsapp,mode FROM store_menu257 WHERE professional_id=?',(pid,)).fetchone()
        assert dest['whatsapp']=='5512988887777' and dest['mode']=='whatsapp'
        assert c.execute('SELECT whatsapp FROM professionals WHERE id=?',(other['id'],)).fetchone()[0]==other['whatsapp']


def test_bad_number_does_not_modify_profile(channel,monkeypatch):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
        before=dict(c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    response=client.post('/painel/perfil',data={'display_name':'Bad','city':'Ubatuba','whatsapp':'123'},follow_redirects=False)
    assert response.status_code==400
    with m.db() as c:
        assert dict(c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone())==before

import os
from pathlib import Path
import subprocess

from test_storeapp257 import channel
from test_storeapp256 import shop
from test_checkout247 import checkout


def test_rendered_store_settings_and_product_areas(channel, monkeypatch):
    m, client, slug, pid, data, product, customer = channel
    for callback in m.app.router.on_startup:
        if callback.__name__ != 'start':
            callback()
    with m.db() as c:
        owner = dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?', (pid,)).fetchone())
        source = dict(c.execute('SELECT * FROM products WHERE id=?', (product,)).fetchone())
        source.pop('id'); source.update(name='Produto comum teste', sold_by_weight370=0)
        keys=list(source)
        c.execute('INSERT INTO products('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')', tuple(source.values()))
        c.execute("UPDATE products SET name='Produto por peso teste',sold_by_weight370=1 WHERE id=?", (product,))
    monkeypatch.setattr(m, 'current_user', lambda request: owner)
    response=client.get('/painel')
    assert response.status_code==200,response.text
    jsdom=os.environ.get('NOWUP_JSDOM',str(Path(__file__).resolve().parents[1]/'node_modules/jsdom'))
    if not Path(jsdom).exists():
        import pytest
        pytest.skip('Set NOWUP_JSDOM to run merchant navigation checks')
    if Path(jsdom).exists():
        result=subprocess.run(['node','tests/merchant-settings.dom.cjs'],input=response.text,text=True,
                              capture_output=True,env={**os.environ,'NOWUP_JSDOM':jsdom})
        assert result.returncode==0,result.stdout+result.stderr

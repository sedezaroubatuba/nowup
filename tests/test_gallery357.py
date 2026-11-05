import io

from PIL import Image
from fastapi.testclient import TestClient

from test_merchant228 import env
import nowup_gallery357 as gallery


def test_library_authentication_and_complete_photo_collection(env):
    main, client, _, store, other = env
    assert TestClient(main.app).get('/painel/galeria-nowup/ingredientes').status_code == 401
    response = client.get('/painel/galeria-nowup/ingredientes')
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 117
    assert len({i['name'].casefold() for i in items}) == len(items)
    assert len({i['category'] for i in items}) == 10
    # Every declared cell must decode into a complete square photo.
    for item in items:
        image = Image.open(io.BytesIO(gallery.photo(item['id'])))
        assert image.format == 'JPEG' and image.size == (1000, 1000)
    assert client.get('/galeria-nowup/ingredientes/not-a-key.jpg').status_code == 404
    assert TestClient(main.app).get('/painel/galeria-nowup/itens-da-loja').status_code == 401


def test_gallery_photo_uses_existing_price_validation_and_store_isolation(env):
    main, client, _, store, other = env
    item = next(i for i in gallery.catalog() if i['name'] == 'Bacon em fatias')
    image = client.get('/galeria-nowup/ingredientes/' + item['id'] + '.jpg')
    assert image.status_code == 200 and image.headers['content-type'] == 'image/jpeg'
    path = '/painel/cardapio/ingredientes320'
    assert client.post(path, data={'name': item['name'], 'price': ''},
                       files={'photo': ('bacon.jpg', image.content, 'image/jpeg')}).status_code == 400
    response = client.post(path, data={'name': item['name'], 'price': '3,50'},
                           files={'photo': ('bacon.jpg', image.content, 'image/jpeg')}, follow_redirects=False)
    assert response.status_code == 303
    with main.db() as conn:
        row = conn.execute('SELECT * FROM ingredients320 WHERE professional_id=? AND name=?',
                           (store, item['name'])).fetchone()
        filename = row['image_filename']
        assert filename and row['price_cents'] == 350
        assert not conn.execute('SELECT id FROM ingredients320 WHERE professional_id=? AND name=?',
                                (other, item['name'])).fetchone()
        assert conn.execute('SELECT price_cents FROM shared_extras155 WHERE id=?',
                            (row['extra_id325'],)).fetchone()[0] == 350
    own = client.get('/painel/galeria-nowup/itens-da-loja').json()
    assert any(i['name'] == item['name'] and i['image_filename'] == filename for i in own)
    foreign_client = TestClient(main.app, headers={'Origin': 'http://testserver'})
    foreign_client.cookies.set('nowup_session', 'other-test')
    with main.db() as conn:
        conn.execute("UPDATE professionals SET is_premium=1,offer_mode='menu',plan_active='ambos' WHERE id=?", (other,))
        conn.commit()
    assert all(i['name'] != item['name'] for i in foreign_client.get('/painel/galeria-nowup/itens-da-loja').json())
    # Repeat import preserves merchant price/photo, rather than overwriting it.
    duplicate = client.post(path, data={'name': item['name'], 'price': '0,00'}, follow_redirects=False)
    assert 'ingrediente-duplicado' in duplicate.headers['location']
    with main.db() as conn:
        row = conn.execute('SELECT price_cents,image_filename FROM ingredients320 WHERE professional_id=? AND name=?',
                           (store, item['name'])).fetchone()
        assert row['price_cents'] == 350 and row['image_filename'] == filename
    panel = client.get('/painel')
    assert panel.status_code == 200
    assert 'data-import-ingredients357' in panel.text and '/static/ingredient-gallery357.js' in panel.text

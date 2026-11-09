import base64
import binascii
import io
import json

from PIL import Image
import pytest

from nowup_pix import field, normalize_key, payload, payment, settings
from test_storeapp257 import channel
from test_storeapp256 import shop
from test_checkout247 import checkout


KEY = '123e4567-e12b-12d1-a456-426655440000'


def parse(code):
    fields = {}; offset = 0
    while offset < len(code):
        tag = code[offset:offset + 2]; size = int(code[offset + 2:offset + 4])
        fields[tag] = code[offset + 4:offset + 4 + size]; offset += 4 + size
    assert offset == len(code)
    return fields


def test_bcb_published_crc_vector():
    # Banco Central Manual de Padrões para Iniciação do Pix, static example.
    code = ('00020126580014br.gov.bcb.pix0136' + KEY +
            '5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***6304')
    assert f'{binascii.crc_hqx(code.encode(), 0xffff):04X}' == '1D3D'


def test_amount_receiver_and_crc_are_exact():
    code = payload(KEY, 'João da Silva', 'São Paulo', 7790, 'NU123')
    fields = parse(code)
    assert fields['54'] == '77.90'
    assert fields['59'] == 'JOAO DA SILVA' and fields['60'] == 'SAO PAULO'
    assert parse(fields['26'])['01'] == KEY
    assert parse(fields['62'])['05'] == 'NU123'
    # Independent bitwise CRC check.
    crc = 0xffff
    for value in code[:-4].encode():
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xffff if crc & 0x8000 else (crc << 1) & 0xffff
    assert fields['63'] == f'{crc:04X}'


@pytest.mark.parametrize('raw,kind,expected', [
    ('(12) 99999-9999', 'phone', '+5512999999999'),
    ('111.444.777-35', 'cpf', '11144477735'),
    ('11.222.333/0001-81', 'cnpj', '11222333000181'),
    ('12.ABC.345/01DE-35', 'cnpj', '12ABC34501DE35'),
    ('LOJA@example.com', 'email', 'loja@example.com'), (KEY.upper(), 'random', KEY)])
def test_explicit_key_types_remove_ambiguity(raw, kind, expected):
    assert normalize_key(raw, kind) == expected


@pytest.mark.parametrize('raw,kind', [('00000000000', 'cpf'), ('1234', 'phone'),
    ('not-a-key', 'random'), ('bad@', 'email'), ('11222333000182', 'cnpj')])
def test_bad_keys_cannot_be_enabled(raw, kind):
    with pytest.raises(ValueError):
        settings(raw, kind, 'Nome', 'Ubatuba')


def test_old_settings_do_not_silently_enable_pix_qr():
    key, kind, _, _ = settings('12999999999', '', '', '')
    assert key == '12999999999' and kind == ''
    assert payment({'pix_key': key}, 1000) is None
    with pytest.raises(ValueError):
        settings(KEY, 'random', '', 'Ubatuba')
    for amount in (0, -1, 1.2, True):
        with pytest.raises(ValueError):
            payload(KEY, 'Nome', 'Ubatuba', amount)


def test_actual_qr_can_be_decoded_back_to_the_exact_payload():
    import zxingcpp as zxing
    result = payment({'pix_key': KEY, 'pix_key_type': 'random',
                      'pix_receiver_name': 'Loja exemplo', 'pix_receiver_city': 'Ubatuba'}, 7790, 'NUABC')
    raw = base64.b64decode(result['qr_image'].split(',')[1])
    decoded = zxing.read_barcode(Image.open(io.BytesIO(raw)))
    assert decoded.text == result['payload']
    assert parse(decoded.text)['54'] == '77.90'


def test_checkout_uses_only_merchant_key_and_server_prices(channel):
    m, client, slug, pid, data, product, customer = channel
    with m.db() as c:
        c.execute('UPDATE professionals SET pix_key=?,pix_key_type=?,pix_receiver_name=?,pix_receiver_city=? WHERE id=?',
                  (KEY, 'random', 'Loja exemplo', 'Ubatuba', pid))
        c.execute('INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,?,?)', (pid, '5512987776666', 'both'))
    data['cart_json'] = json.dumps([{'id': product, 'quantity': 2, 'price': 1}])
    data['pix_key'] = 'bad-client-key'
    response = client.post('/p/' + slug + '/menu/whatsapp', data=data)
    assert response.status_code == 200, response.text
    result = response.json()
    assert 'pix' not in result and 'pix' not in result['receipt']
    assert result['review_required'] is True
    assert result['receipt']['order_code'] == result['order_code']
    assert client.post('/p/' + slug + '/menu/whatsapp', data=data).json() == result
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 1
        assert c.execute('SELECT status FROM orders').fetchone()[0] == 'new'
    before = client.get(result['redirect'])
    assert before.status_code == 200
    assert 'data-pix-payment' not in before.text
    with m.db() as c:
        c.execute("UPDATE orders SET status='confirmed'")
    after = client.get(result['redirect'])
    assert after.status_code == 200
    assert 'data-pix-payment' in after.text and 'data:image/png;base64,' in after.text
    from bs4 import BeautifulSoup
    script=BeautifulSoup(after.text,'html.parser').select_one('[data-pix-payment] script')
    fields=parse(json.loads(script.string)['payload'])
    assert fields['54']=='6.00' and parse(fields['26'])['01']==KEY



def test_only_the_authenticated_merchant_settings_are_updated(channel, monkeypatch):
    m, client, slug, pid, data, product, customer = channel
    with m.db() as c:
        owner = dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?', (pid,)).fetchone())
        other = dict(c.execute('SELECT * FROM professionals WHERE id<>? LIMIT 1', (pid,)).fetchone())
    monkeypatch.setattr(m, 'current_user', lambda request: owner)
    values = {'pix_key': KEY, 'pix_key_type': 'random', 'pix_receiver_name': 'Loja exemplo',
              'pix_receiver_city': 'Ubatuba', 'delivery_fee': '5,00', 'minimum_order': '10,00',
              'allows_delivery': '1', 'allows_pickup': '1'}
    response = client.post('/painel/cardapio/configuracoes', data=values, follow_redirects=False)
    assert response.status_code == 303, response.text
    with m.db() as c:
        own = c.execute('SELECT * FROM professionals WHERE id=?', (pid,)).fetchone()
        assert own['pix_key'] == KEY and own['pix_key_type'] == 'random'
        assert own['delivery_fee_cents'] == 500
        assert dict(c.execute('SELECT * FROM professionals WHERE id=?', (other['id'],)).fetchone()) == other
    values['pix_key'] = 'bad'
    assert client.post('/painel/cardapio/configuracoes', data=values).status_code == 400

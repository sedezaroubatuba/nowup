import json

from nowup_whatsapp_receipt import build


def example(items, **overrides):
    values = dict(store={'display_name': 'Lanchonete do João', 'slug': 'joao'},
                  name='Cliente exemplo', phone='12999999999', items=items,
                  subtotal=7290, fee=500, total=7790, fulfillment='delivery',
                  address='Rua de exemplo, 10', neighborhood='Centro', reference='Portão azul',
                  payment='pix', change=0, notes='Não tocar a campainha')
    values.update(overrides)
    return build(**values)


def combo():
    pack = {'version': 1, 'items': [
        {'name': 'X-bacon', 'quantity': 2, 'role': 'principal', 'product_id': 7},
        {'name': 'Batata frita média', 'quantity': 1, 'role': 'included'},
        {'name': 'Refrigerante 1 litro', 'quantity': 1, 'role': 'included'}],
        'units364': [
            {'name': 'X-bacon', 'product_id': 7, 'position': 1,
             'notes': 'Retirar: cebola, tomate · Carne bem passada',
             'options': [{'name': 'Queijo extra', 'price_cents': 300}]},
            {'name': 'X-bacon', 'product_id': 7, 'position': 2,
             'notes': 'Retirar: alface', 'options': []}]}
    return ({'name': 'Combo Dois X-bacon', 'combo_pack305': json.dumps(pack)}, 1,
            'Flattened notes must not duplicate the units',
            [{'name': 'X-bacon 1: Queijo extra', 'price_cents': 300}], 7290)


def test_unit_changes_and_extras_stay_with_the_correct_burger():
    receipt, message = example([combo()])
    first, second = [b for b in receipt['blocks'] if 'UNIDADE' in b['title']]
    assert first['lines'] == ['Retirar: cebola', 'Retirar: tomate', 'Carne bem passada',
                              'Adicionar: Queijo extra (+R$ 3,00)']
    assert second['lines'] == ['Retirar: alface']
    assert message.count('Queijo extra') == 1
    assert 'Flattened' not in message
    assert '1 × Batata frita média' in message
    assert receipt['total'] == 'R$ 77,90'


def test_multiple_identical_combos_explain_scope_without_multiplying_components():
    item = list(combo()); item[1] = 2
    receipt, message = example([tuple(item)], subtotal=14580, total=15080)
    assert 'cada um dos 2 combos' in message
    assert receipt['total'] == 'R$ 150,80'
    assert '1 × Batata' in message


def test_plain_products_and_delivery_details_keep_every_note():
    receipt, message = example([({'name': 'Produto simples'}, 2, 'Retirar: tomate · Sem sal', [], 1000)])
    for value in ('Retirar: tomate', 'Sem sal', 'Portão azul', 'Não tocar a campainha',
                  'Rua de exemplo, 10', 'Subtotal: R$ 72,90', 'Entrega: R$ 5,00'):
        assert value in message
    assert receipt['logo'] == '/p/joao/app-icon/192.png'


def test_pickup_hides_delivery_address_and_cash_shows_change():
    receipt, message = example([({'name': 'Água'}, 1, '', [], 500)],
                               fulfillment='pickup', reference='', payment='cash', change=10000)
    assert 'Retirada no local' in message and 'Endereço:' not in message
    assert 'Troco para: R$ 100,00' in message


def test_included_items_keep_group_names_when_no_editable_units_exist():
    pack = {'version': 1, 'items': [
        {'name': 'Red Bull tropical 250ml', 'quantity': 4, 'role': 'included', 'group': 'Energético'},
        {'name': 'Canudo', 'quantity': 4, 'role': 'manual'}], 'note': 'Gelado'}
    receipt, message = example([({'name': 'Combo', 'combo_pack305': json.dumps(pack)}, 1, '', [], 1000)])
    assert 'Energético: 4 × Red Bull tropical 250ml' in message
    assert '4 × Canudo' in message and 'Observação: Gelado' in message

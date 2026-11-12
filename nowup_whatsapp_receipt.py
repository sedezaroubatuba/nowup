"""Presentation of validated checkout snapshots; never calculates order prices."""
from collections import Counter
from urllib.parse import quote

from nowup_combo_pack305 import read_pack
from nowup_order_layout347 import note_lines


def money(cents):
    return 'R$ ' + f'{cents / 100:.2f}'.replace('.', ',')


def details(value):
    result = []
    for line in note_lines(value):
        if line.startswith('Retirar: '):
            result.extend('Retirar: ' + item.strip() for item in line[9:].split(',') if item.strip())
        else:
            result.append(line)
    return result


def build(store, name, phone, items, subtotal, fee, total, fulfillment,
          address, neighborhood, reference, payment, change, notes):
    blocks = [{'title': 'CLIENTE', 'lines': ['Nome: ' + name, 'WhatsApp: ' + phone]}]
    for index, (product, quantity, item_notes, chosen, unit_price) in enumerate(items, 1):
        pack = read_pack(product.get('combo_pack305', ''))
        units = pack.get('units364', []) if pack else []
        lines = ['Valor dos itens: ' + money(unit_price * quantity)]
        if quantity > 1:
            lines.append('Valor por unidade: ' + money(unit_price))
        if units and quantity > 1:
            lines.append('As escolhas abaixo valem para cada um dos ' + str(quantity) + ' combos.')
        blocks.append({'title': f"ITEM {index} • {quantity}x {product['name']}",
                       'lines': lines, 'kind': 'item'})
        # Per-unit extras are also present in chosen; show each once, under its unit.
        unit_extras = Counter((u['name'] + ' ' + str(u['position']) + ': ' + o['name'],
                               o['price_cents']) for u in units for o in u.get('options', []))
        top_extras = []
        for extra in chosen:
            key = (extra['name'], extra['price_cents'])
            if unit_extras[key]:
                unit_extras[key] -= 1
            else:
                top_extras.append('Adicionar: ' + extra['name'] + ' (+' + money(extra['price_cents']) + ')')
        if pack:
            if pack.get('notice316'):
                blocks.append({'title': 'AVISO DO COMBO', 'lines': details(pack['notice316'])})
            editable_ids = {u.get('product_id') for u in units}
            included = []
            for row in pack['items']:
                if row.get('product_id') in editable_ids:
                    continue
                label = (str(row.get('group', '')).strip() + ': ') if row.get('group') else ''
                included.append(label + str(row['quantity']) + ' × ' + row['name'])
            for u in units:
                unit_lines = details(u.get('notes', ''))
                if not unit_lines:
                    unit_lines = ['Sem alterações nos ingredientes.']
                unit_lines.extend('Adicionar: ' + o['name'] + ' (+' + money(o['price_cents']) + ')'
                                  for o in u.get('options', []))
                blocks.append({'title': u['name'] + ' • UNIDADE ' + str(u['position']),
                               'lines': unit_lines, 'kind': 'unit'})
            if included:
                blocks.append({'title': 'ITENS INCLUÍDOS • POR COMBO', 'lines': included, 'kind': 'unit'})
            other = details(pack.get('details365', '')) + top_extras
            if pack.get('note'):
                other += ['Observação: ' + pack['note']]
            if other:
                blocks.append({'title': 'OUTROS DETALHES DO ITEM ' + str(index), 'lines': other})
        elif item_notes or top_extras:
            blocks.append({'title': 'DETALHES DO ITEM ' + str(index),
                           'lines': details(item_notes) + top_extras, 'kind': 'unit'})
    receiving = ['Entrega' if fulfillment == 'delivery' else 'Retirada no local']
    if fulfillment == 'delivery':
        receiving += ['Endereço: ' + address.strip(), 'Bairro: ' + neighborhood]
    if reference.strip():
        receiving += ['Referência: ' + reference.strip()]
    blocks.append({'title': 'RECEBIMENTO', 'lines': receiving})
    labels = {'pix': 'Pix', 'cash': 'Dinheiro', 'credit': 'Cartão de crédito',
              'debit': 'Cartão de débito', 'on_delivery': 'Combinar no atendimento'}
    paying = [labels[payment]]
    if payment in ('credit','debit'):
        paying += ['Pagamento na entrega ou retirada.', 'LEVAR MAQUININHA' if fulfillment=='delivery' else 'Preparar maquininha na retirada.']
    if payment=='cash':
        paying.append('Troco para: '+money(change)+' — Troco: '+money(max(0,change-total)) if change else 'Sem troco.')
    blocks.append({'title': 'PAGAMENTO', 'lines': paying})
    if notes.strip():
        blocks.append({'title': 'OBSERVAÇÕES DO PEDIDO', 'lines': notes.strip().splitlines()})
    blocks.append({'title': 'VALORES', 'lines': ['Subtotal: ' + money(subtotal), 'Entrega: ' + money(fee)]})
    receipt = {'version': 1, 'store_name': store['display_name'],
               'logo': '/p/' + quote(store['slug'], safe='') + '/app-icon/192.png',
               'status': 'Aguardando confirmação da loja', 'blocks': blocks,
               'total': money(total)}
    lines = ['*NOVO PEDIDO — NOWUP*', receipt['store_name'], '']
    for block in blocks:
        lines += ['*' + block['title'] + '*'] + ['• ' + line for line in block['lines']] + ['']
    lines += ['*Total: ' + receipt['total'] + '*', '', receipt['status']]
    return receipt, '\n'.join(lines)

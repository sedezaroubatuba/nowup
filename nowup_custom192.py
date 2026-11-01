"""Product-level included choices, removals and optional free extras."""
import json
from fastapi import HTTPException


def fail(message):
    raise HTTPException(400, message)


def integer(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        fail(label + ': quantidade inválida.')
    return value


def names(values, label, limit=40):
    if not isinstance(values, list) or len(values) > limit:
        fail(label + ': lista inválida.')
    result = []
    for value in values:
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 140:
            fail(label + ': nome inválido.')
        value = value.strip()
        if value.casefold() in {s.casefold() for s in result}:
            fail(label + ': não repita os itens.')
        result.append(value)
    return result


def parse_config(raw):
    if not raw:
        return {'ingredients': [], 'groups': [], 'free_enabled': False, 'free_count': 0,
                'utensils': True, 'notes': True}
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        fail('Personalização inválida.')
    if not isinstance(data, dict):
        fail('Personalização inválida.')
    for key in ('free_enabled', 'utensils', 'notes'):
        if key in data and not isinstance(data[key], bool):
            fail('Personalização inválida.')
    ingredients = data.get('ingredients', [])
    if not isinstance(ingredients, list) or len(ingredients) > 40:
        fail('Cadastre até 40 ingredientes.')
    if any(not isinstance(i, dict) or not isinstance(i.get('removable', True), bool) for i in ingredients):
        fail('Ingredientes inválidos.')
    clean_names = names([i.get('name') for i in ingredients], 'Ingredientes')
    clean_ingredients = [{'name': name, 'removable': ingredients[i].get('removable', True)} for i, name in enumerate(clean_names)]
    groups = data.get('groups', [])
    if not isinstance(groups, list) or len(groups) > 10:
        fail('Cadastre até 10 grupos de opções.')
    clean_groups = []
    ids = set()
    for group in groups:
        if not isinstance(group, dict):
            fail('Grupo inválido.')
        gid = group.get('id')
        if not isinstance(gid, str) or not gid.isalnum() or len(gid) > 40 or gid in ids:
            fail('Identificador do grupo inválido.')
        ids.add(gid)
        title = names([group.get('name')], 'Grupo')[0]
        options = names(group.get('options'), title, 30)
        quantity_mode = group.get('quantity_mode', False)
        if not isinstance(quantity_mode, bool):fail('Modo de quantidade inválido.')
        maximum = integer(group.get('max', 1), 1, 99 if quantity_mode else len(options), title)
        minimum = integer(group.get('min', 0), 0, maximum, title)
        clean_group = {'id': gid, 'name': title, 'min': minimum, 'max': maximum, 'options': options}
        if quantity_mode:clean_group['quantity_mode'] = True
        if 'product_ids' in group:
            refs = group['product_ids']
            if not isinstance(refs, list) or len(refs) != len(options):
                fail('Selecione os produtos das opções de troca.')
            clean_group['product_ids'] = [integer(ref, 1, 2147483647, title) for ref in refs]
        clean_groups.append(clean_group)
    free_enabled = data.get('free_enabled', False)
    output = {'ingredients': clean_ingredients, 'groups': clean_groups,
            'free_enabled': free_enabled, 'free_count': integer(data.get('free_count', 0), 0, 20, 'Gratuitos') if free_enabled else 0,
            'utensils': data.get('utensils', False), 'notes': data.get('notes', True)}
    items = data.get('combo_items', [])
    if not isinstance(items, list) or len(items) > 40 or any(not isinstance(item, dict) for item in items):
        fail('Cadastre até 40 itens no combo.')
    item_names = names([item.get('name') for item in items], 'Itens do combo')
    output['combo_items'] = [{'name': name, 'quantity': integer(items[i].get('quantity'), 1, 99, name)} for i, name in enumerate(item_names)]
    for index, item in enumerate(items):
        if 'product_id' in item:
            output['combo_items'][index]['product_id'] = integer(item['product_id'], 1, 2147483647, 'Produto do combo')
        if 'principal' in item and not isinstance(item['principal'], bool):fail('Produto principal inválido.')
        if item.get('principal'):
            if item.get('group_id301'):fail('O produto principal deve ser fixo, sem grupo de escolhas.')
            output['combo_items'][index]['principal'] = True
        if item.get('group_id301'):
            gid = item['group_id301']
            if not isinstance(gid, str) or not gid.isalnum() or len(gid) > 40:fail('Grupo do combo inválido.')
            output['combo_items'][index]['group_id301'] = gid
    if sum(bool(i.get('principal')) for i in output['combo_items']) > 1:fail('Selecione somente um produto principal por combo.')
    manual = data.get('combo_manual', [])
    if not isinstance(manual, list) or len(manual) > 20 or any(not isinstance(i, dict) for i in manual):fail('Itens manuais inválidos.')
    manual_names = names([i.get('name') for i in manual], 'Itens manuais', 20)
    output['combo_manual'] = [{'name': name, 'quantity': integer(manual[i].get('quantity'), 1, 99, name)} for i, name in enumerate(manual_names)]
    if 'included195' in data:output['included195'] = data['included195']
    return output


def bind_combo_products(conn, professional_id, config, product_id=None):
    """Resolve references using this store only; names/prices from requests are untrusted."""
    rows = conn.execute("SELECT id,name,available,is_combo256,category FROM products WHERE professional_id=?", (professional_id,)).fetchall()
    catalog = {row['id']: row for row in rows if row['id'] != product_id and not row['is_combo256'] and row['category'].casefold() != 'combos'}
    def resolve(ref, name):
        if ref is None:  # Migrate old text entries only when an exact store product exists.
            matches = [row for row in catalog.values() if row['name'].casefold() == name.casefold()]
            row = matches[0] if len(matches) == 1 else None
        else:
            row = catalog.get(integer(ref, 1, 2147483647, 'Produto do combo'))
        if row is None or not row['available']:
            fail('Selecione um produto disponível da própria loja para cada item e opção do combo.')
        return row
    if not config.get('combo_items'):
        fail('Selecione pelo menos um produto para compor o combo.')
    items = []
    seen = set()
    for item in config.get('combo_items', []):
        row = resolve(item.get('product_id'), item['name'])
        if row['id'] in seen:
            fail('Não repita o produto no combo. Ajuste a quantidade.')
        seen.add(row['id'])
        entry = {'product_id': row['id'], 'name': row['name'], 'quantity': item['quantity']}
        if item.get('group_id301'):entry['group_id301'] = item['group_id301']
        if item.get('principal'):entry['principal'] = True
        items.append(entry)
    config['combo_items'] = items
    for group in config['groups']:
        refs = group.get('product_ids', [None] * len(group['options']))
        resolved = [resolve(ref, name) for ref, name in zip(refs, group['options'])]
        if len({row['id'] for row in resolved}) != len(resolved):
            fail('Não repita produtos no mesmo grupo de escolhas.')
        group['product_ids'] = [row['id'] for row in resolved]
        group['options'] = [row['name'] for row in resolved]
    for item in items:
        if item.get('group_id301'):
            group = next((g for g in config['groups'] if g['id'] == item['group_id301']), None)
            if not group or not group.get('quantity_mode') or group['min'] != item['quantity'] or group['max'] != item['quantity'] or item['product_id'] not in group.get('product_ids', []):
                fail('Confira os produtos e as quantidades do grupo do combo.')
    return config


def save_config(conn, product_id, config):
    conn.execute('UPDATE products SET customization192=? WHERE id=?',
                 (json.dumps(config, ensure_ascii=False), product_id))
    if config['ingredients'] or config['groups'] or config['utensils']:
        conn.execute('UPDATE products SET is_dish=1 WHERE id=?', (product_id,))


def charge_options(chosen, config):
    # Favor the customer: the most expensive selected extras use the free allowance.
    free = {o['id'] for o in sorted(chosen, key=lambda o: (-o['price_cents'], o['id']))[:config['free_count']]}
    result = [{**dict(o), 'price_cents': 0 if o['id'] in free else o['price_cents']} for o in chosen]
    return result, sum(o['price_cents'] for o in result)


def validate_customization(config, raw, notes, utensils):
    if not isinstance(raw, dict):
        fail('Escolhas do produto inválidas.')
    removed = names(raw.get('removed', []), 'Retiradas')
    removable = {i['name'] for i in config['ingredients'] if i['removable']}
    if not set(removed) <= removable:
        fail('Um ingrediente não pode ser retirado. Atualize o produto.')
    groups = raw.get('groups', {})
    if not isinstance(groups, dict) or not set(groups) <= {g['id'] for g in config['groups']}:
        fail('As opções do produto mudaram. Atualize o produto.')
    parts = []
    if notes and not config['notes']:
        fail('Este produto não aceita observações.')
    if notes:
        parts.append(notes[:300])
    if removed:
        parts.append('Retirar: ' + ', '.join(removed))
    for group in config['groups']:
        raw_values = groups.get(group['id'], [])
        if group.get('quantity_mode'):
            if not isinstance(raw_values, list) or len(raw_values) > 99 or any(not isinstance(v, str) or not v.strip() or len(v) > 140 for v in raw_values):fail('Quantidades do combo inválidas.')
            values = raw_values
        else:
            values = names(raw_values, group['name'], 30)
        if not set(values) <= set(group['options']):
            fail(group['name'] + ': uma opção não está mais disponível.')
        if not group['min'] <= len(values) <= group['max']:
            fail(f"{group['name']}: escolha de {group['min']} a {group['max']} opções.")
        if values:
            parts.append(group['name'] + ': ' + ', '.join((str(values.count(v)) + ' × ' + v) if group.get('quantity_mode') else v for v in dict.fromkeys(values)))
    if not isinstance(utensils, bool):
        fail('Opção de talheres inválida.')
    principal = [i for i in config.get('combo_items', []) if i.get('principal')]
    if principal:parts.append('Produto principal: ' + ', '.join(str(i['quantity']) + ' × ' + i['name'] for i in principal))
    if config.get('combo_manual'):
        parts.append('Incluído: ' + ', '.join(str(i['quantity']) + ' × ' + i['name'] for i in config['combo_manual']))
    if utensils and not config['utensils']:
        fail('Talheres não estão disponíveis para este produto.')
    if config['utensils']:
        parts.append('Talheres: sim (garfo e faca)' if utensils else 'Talheres: não')
    return ' · '.join(parts)




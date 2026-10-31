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
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
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
        maximum = integer(group.get('max', 1), 1, len(options), title)
        minimum = integer(group.get('min', 0), 0, maximum, title)
        clean_groups.append({'id': gid, 'name': title, 'min': minimum, 'max': maximum, 'options': options})
    free_enabled = data.get('free_enabled', False)
    output = {'ingredients': clean_ingredients, 'groups': clean_groups,
            'free_enabled': free_enabled, 'free_count': integer(data.get('free_count', 0), 0, 20, 'Gratuitos') if free_enabled else 0,
            'utensils': data.get('utensils', False), 'notes': data.get('notes', True)}
    items = data.get('combo_items', [])
    if not isinstance(items, list) or len(items) > 40 or any(not isinstance(item, dict) for item in items):
        fail('Cadastre até 40 itens no combo.')
    item_names = names([item.get('name') for item in items], 'Itens do combo')
    output['combo_items'] = [{'name': name, 'quantity': integer(items[i].get('quantity'), 1, 99, name)} for i, name in enumerate(item_names)]
    if 'included195' in data:output['included195'] = data['included195']
    return output


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
        values = names(groups.get(group['id'], []), group['name'], 30)
        if not set(values) <= set(group['options']):
            fail(group['name'] + ': uma opção não está mais disponível.')
        if not group['min'] <= len(values) <= group['max']:
            fail(f"{group['name']}: escolha de {group['min']} a {group['max']} opções.")
        if values:
            parts.append(group['name'] + ': ' + ', '.join(values))
    if not isinstance(utensils, bool):
        fail('Opção de talheres inválida.')
    if utensils and not config['utensils']:
        fail('Talheres não estão disponíveis para este produto.')
    if config['utensils']:
        parts.append('Talheres: sim (garfo e faca)' if utensils else 'Talheres: não')
    return ' · '.join(parts)

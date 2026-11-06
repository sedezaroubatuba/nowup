"""Fixed-price portions: integer grams and cents, never a post-weighing surcharge."""
from fastapi import HTTPException

MAX_GRAMS = 99900
NOTICE = 'Separe o peso solicitado ou o mais próximo acima. Não cobre pelo excedente.'


def grams(value):
    if type(value) is not int or not 100 <= value <= MAX_GRAMS or value % 100:
        raise HTTPException(400, 'Escolha o peso em intervalos de 100 g, de 100 g a 99,9 kg.')
    return value


def portion_cents(price_per_kg, weight):
    grams(weight)
    if type(price_per_kg) is not int or not 1 <= price_per_kg <= 10000000:
        raise HTTPException(400, 'Informe um preço por kg válido.')
    # Round HALF_UP once, after multiplying. Never round a 100 g price first.
    return (price_per_kg * weight + 500) // 1000


def weight_label(weight):
    return (str(weight // 1000) + (',' + str(weight % 1000 // 100) if weight % 1000 else '') + ' kg (' + f'{weight:,}'.replace(',', '.') + ' g)') if weight >= 1000 else str(weight) + ' g'


def configure(price, combo, extras, config):
    portion_cents(price, 100)
    if combo or extras not in ('none', 'legacy') or config:
        raise HTTPException(400, 'Produtos por peso têm cadastro básico, sem combos, adicionais ou personalização.')


def apply_line(product, raw, qty, notes, chosen):
    weight = raw.get('weight_grams370')
    if not product.get('sold_by_weight370'):
        if weight is not None:
            raise HTTPException(400, 'Este produto é vendido por unidade.')
        return None
    grams(weight)
    if product.get('is_combo256') or product.get('is_dish'):
        raise HTTPException(400, 'Produtos por peso não participam de combos ou refeições.')
    if qty != 1 or chosen or raw.get('utensils') or any(raw.get('customization', {}).get(k) for k in ('removed', 'groups', 'units364')):
        raise HTTPException(400, 'Escolha apenas o peso para este produto.')
    from nowup_combos303 import current_price
    rate = current_price(product)
    total = portion_cents(rate, weight)
    product['weight_grams370'] = weight
    product['price_per_kg370'] = rate
    product['name'] += ' — ' + weight_label(weight)
    note = f"{NOTICE} Preço por kg: R$ {rate // 100},{rate % 100:02d}."
    return total, note + (' Obs.: ' + notes if notes else '')


def snapshot(conn, item_id, product):
    if product.get('weight_grams370'):
        conn.execute('UPDATE order_items SET weight_grams370=?,price_per_kg370=? WHERE id=?',
                     (product['weight_grams370'], product['price_per_kg370'], item_id))

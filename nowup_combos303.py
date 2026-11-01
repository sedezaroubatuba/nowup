"""Read-only current catalog prices for comparing combos with separate purchases."""
from fastapi import HTTPException
from nowup_custom192 import parse_config


def combo_kind(category, value):
    legacy=category.strip().casefold()=='__combos256'
    enabled=legacy or (category.strip().casefold()=='combos' if value is None else str(value).lower() in ('1','true','yes','sim'))
    return enabled, 'Combos' if legacy else category


def current_price(row):
    promo=int(row['promo_price_cents'] or 0)
    return promo if 0 < promo < int(row['price_cents']) else int(row['price_cents'])


def attach_prices(conn, store_id, products):
    catalog=conn.execute('SELECT id,price_cents,promo_price_cents,image_filename FROM products WHERE professional_id=? AND available=1 AND is_combo256=0',(store_id,)).fetchall()
    prices={str(r['id']):current_price(r) for r in catalog}
    images={str(r['id']):r['image_filename'] for r in catalog if r['image_filename']}
    output=[]
    for source in products:
        row=dict(source);row['combo_prices303']={};row['combo_images303']={}
        if row.get('is_combo256'):
            try:
                config=parse_config(row.get('customization192',''))
                ids={str(i['product_id']) for i in config.get('combo_items',[]) if i.get('product_id')}
                for group in config.get('groups',[]):ids.update(str(i) for i in group.get('product_ids',[]))
                row['combo_prices303']={key:prices[key] for key in ids if key in prices}
                row['combo_images303']={key:images[key] for key in ids if key in images}
            except (ValueError,TypeError,KeyError,HTTPException):pass
        output.append(row)
    return output

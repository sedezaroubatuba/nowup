"""V91: vitrine de alimentos; não altera dados ou categorias."""
import hashlib
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

ASSETS = '<link rel="stylesheet" href="/static/nowup-food91.css?v=91"><script defer src="/static/nowup-food91.js?v=91"></script>'

def attach_food_assets(response):
    body = response.body
    if b'nowup-food91.js' not in body:
        assets = ASSETS.encode()
        body = body.replace(b'</body>', assets + b'</body>', 1) if b'</body>' in body else body + assets
        response.body = body
        response.headers['content-length'] = str(len(body))
    return response

def daily_mix(groups, day, limit=180):
    """Intercala lojas; a posição inicial avança a cada dia."""
    ordinal = datetime.strptime(day, '%Y-%m-%d').date().toordinal()
    stores = sorted(groups)
    if not stores: return []
    offset = ordinal % len(stores)
    stores = stores[offset:] + stores[:offset]
    pools = {}
    for sid in stores:
        items = sorted(groups[sid], key=lambda p: hashlib.sha256(str(p['id']).encode()).digest())
        shift = ordinal % len(items)
        pools[sid] = items[shift:] + items[:shift]
    result = []
    depth = 0
    while len(result) < limit:
        batch = [pools[sid][depth] for sid in stores if len(pools[sid]) > depth]
        if not batch: break
        result.extend(batch[:limit-len(result)])
        depth += 1
    return result

def register_food_feed(app, db, get_settings, active_cities, shop_status, public_scope):
    @app.get('/api/experimente-hoje')
    def food_feed(city: str = ''):
        from fastapi.responses import JSONResponse
        conn = db()
        try:
            cities = active_cities(get_settings(conn))
            city = city.strip() or cities[0]
            stores = conn.execute(f"""SELECT p.* FROM professionals p
                WHERE p.blocked=0 AND p.admission_status='approved'
                AND p.is_premium=1 AND p.offer_mode='menu'
                AND p.city LIKE ? AND {public_scope()}
                ORDER BY p.id""", ('%' + city + '%',)).fetchall()
            groups = {}
            for raw in stores:
                store = dict(raw)
                if not shop_status(store)['open']: continue
                rows = conn.execute("""SELECT pr.* FROM products pr
                    WHERE pr.professional_id=? AND pr.available=1
                    AND pr.max_quantity>0 AND trim(pr.image_filename)!=''
                    AND (NOT EXISTS(SELECT 1 FROM product_categories pc
                        WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category))
                      OR EXISTS(SELECT 1 FROM product_categories pc
                        WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category) AND pc.active=1))
                    ORDER BY pr.id""", (store['id'],)).fetchall()
                items = []
                for row in rows:
                    p = dict(row)
                    price = p['promo_price_cents'] if p['promo_price_cents'] > 0 else p['price_cents']
                    items.append({'id': p['id'], 'name': p['name'], 'shop': store['display_name'],
                        'price_cents': price, 'image': '/uploads/' + quote(p['image_filename'], safe=''),
                        'url': '/p/' + quote(store['slug'], safe='') + '/menu?produto=' + str(p['id']),
                        'product_name': p['name']})
                if items: groups[store['id']] = items
            day = datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat()
            return JSONResponse({'day': day, 'city': city, 'items': daily_mix(groups, day)},
                headers={'Cache-Control': 'no-store'})
        finally:
            conn.close()

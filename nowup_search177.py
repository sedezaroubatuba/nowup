"""Public catalog search; uses current data and makes no database mutations."""
import secrets
import unicodedata
from urllib.parse import quote


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(value or '')) if not unicodedata.combining(c)).casefold().strip()


def relevance(name, description, category, query):
    n=normalize(name)
    if n==query:return 0
    if query in n:return 1
    if all(t in n for t in query.split()):return 2
    return 3


def rank_products(rows, query, city, random_key=None):
    random_key=random_key or (lambda _: secrets.randbits(32))
    local=normalize(city)=='ubatuba'
    return sorted(rows,key=lambda r:(0 if local and r['store_slug']=='samuel-dos-santos-silva' else 1,
        relevance(r['name'],r['description'],r['category'],query),random_key(r)))


def register(app, db, public_business_scope, shop_status):
    from nowup_vitrine473 import browse_item
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.get('/api/busca177')
    def search(request: Request,q: str='',city: str='',category: str='',open_now: str=''):
        query=normalize(q[:80]);tokens=query.split()[:8]
        if len(query)<2 or not tokens:
            return JSONResponse({'products':[],'stores':[]},headers={'Cache-Control':'no-store'})
        conn=db()
        try:
            if not city.strip():
                city_row=conn.execute("SELECT city FROM professionals WHERE city!='' AND blocked=0 AND admission_status='approved' ORDER BY id LIMIT 1").fetchone()
                city=city_row['city'] if city_row else 'Ubatuba'
            scope="p.blocked=0 AND p.admission_status='approved' AND "+public_business_scope()
            params=[]
            city_key=normalize(city)
            if category:
                scope+=' AND EXISTS(SELECT 1 FROM professional_categories pc JOIN categories c ON c.id=pc.category_id WHERE pc.professional_id=p.id AND c.active=1 AND c.slug=?)'
                params.append(category[:100])
            def matches(*fields):
                text = normalize(" ".join(str(value or "") for value in fields))
                return all(token in text for token in tokens)
            # Cardapio-only stores have a private external menu and are excluded.
            product_sql='''SELECT pr.*,p.business_type,
                p.slug,p.slug store_slug,p.display_name,p.display_name store_name,p.city,p.neighborhood,p.business_hours,p.business_status,
                p.id professional_id FROM products pr JOIN professionals p ON p.id=pr.professional_id
                WHERE '''+scope+''' AND p.plan_active IN ('ambos','completo') AND p.is_premium=1 AND p.offer_mode IN ('menu','catalog') AND pr.available=1 AND pr.is_group_header260=0
                AND (pr.group_parent_id260=0 OR EXISTS (SELECT 1 FROM products parent WHERE parent.id=pr.group_parent_id260 AND parent.professional_id=p.id AND parent.available=1))
                AND (NOT EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=p.id AND lower(pc.name)=lower(pr.category))
                OR EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=p.id AND lower(pc.name)=lower(pr.category) AND pc.active=1))'''
            products=[]
            for row in conn.execute(product_sql,params):
                r=dict(row)
                if normalize(r['city']) != city_key or not matches(r['name'],r['description'],r['category']):
                    continue
                if open_now=='1' and not shop_status(r)['open']:
                    continue
                products.append(r)
            products=rank_products(products,query,city)[:30]
            stores=[]
            for row in conn.execute('SELECT p.* FROM professionals p WHERE '+scope,params):
                r=dict(row)
                if normalize(r['city']) != city_key or not matches(r['display_name'],r['description'],r['services']):
                    continue
                status=shop_status(r)
                if open_now=='1' and not status['open']:
                    continue
                stores.append((r,status))
            stores.sort(key=lambda item:(relevance(item[0]['display_name'],'','',query),secrets.randbits(32)))
            def image(filename):return '/uploads/'+quote(filename,safe='') if filename else ''
            payload=[]
            for r in products:
                status=shop_status(r)
                item=browse_item(r,status)
                payload.append({'cart':{'id':r['id'],'name':r['name'],'price':item['price'],'max':r['max_quantity'],'slug':r['store_slug'],'store':r['store_name'],'options':item['requires_options']},'id':r['id'],'name':r['name'],'store_name':r['store_name'],'city':r['city'],
                    'price_cents':item['price'],
                    'image':image(r['image_filename']),'open':bool(status['open']),
                    'url':'/p/'+quote(r['store_slug'],safe='')+'/menu?produto='+str(r['id'])+'#produto-'+str(r['id'])})
            return JSONResponse({'products':payload,'stores':[{'name':r['display_name'],'city':r['city'],'open':bool(status['open']),
                'image':image(r['cover_filename'] or r['avatar_filename']),'url':'/p/'+quote(r['slug'],safe='')} for r,status in stores[:15]]},headers={'Cache-Control':'no-store'})
        finally:conn.close()

"""Public catalog search; uses current data and makes no database mutations."""
import re
import secrets
import unicodedata
from urllib.parse import quote


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(value or '')) if not unicodedata.combining(c)).casefold().strip()


def search_words(value):
    return re.findall(r"[^\W_]+", normalize(value))


OFFER_WORDS = {"promocao", "promocoes", "oferta", "ofertas", "desconto", "descontos", "promocional"}
COMBO_WORDS = {"combo", "combos", "kit", "kits"}
CATEGORY_ALIASES = {
    "cerveja": ("cervejas", "cerveja", "chopp"),
    "refrigerante": ("refrigerante", "refrigerantes", "refri", "refris"),
}


def matches_product(row, tokens, promo):
    words = search_words(" ".join(str(row.get(key) or "") for key in (
        "name", "description", "category", "subcategory_name",
    )))
    category = normalize(row.get("category"))
    name = normalize(row.get("name"))
    aliases = []
    if "cerveja" in category or "chopp" in category:
        aliases.extend(CATEGORY_ALIASES["cerveja"])
    if "refrigerante" in name or ("bebidas nao alco" in category and not any(
        word in words for word in ("agua", "suco", "energetico", "isotonico")
    )):
        aliases.extend(CATEGORY_ALIASES["refrigerante"])
    terms = words + aliases
    compact = "".join(words)
    for token in tokens:
        if token in OFFER_WORDS:
            if not promo:
                return False
        elif token in COMBO_WORDS:
            if not (row.get("is_combo256") or "combo" in words or "combos" in words):
                return False
        elif not any(token in term or (token.endswith("s") and len(token) > 3 and token[:-1] in term)
                     for term in terms) and token not in compact:
            return False
    return True


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
    from nowup_vitrine473 import browse_item, is_vitrine_product
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.get('/api/busca177')
    def search(request: Request,q: str='',city: str='',category: str='',open_now: str=''):
        tokens=search_words(q[:80])[:8];query=' '.join(tokens)
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
                (SELECT sc.name FROM product_subcategories261 sc WHERE sc.id=pr.subcategory_id261 AND sc.professional_id=p.id AND sc.active=1) subcategory_name
                FROM products pr JOIN professionals p ON p.id=pr.professional_id
                WHERE '''+scope+''' AND p.plan_active IN ('ambos','completo') AND p.is_premium=1 AND p.offer_mode IN ('menu','catalog') AND pr.available=1 AND pr.is_group_header260=0
                AND (pr.group_parent_id260=0 OR EXISTS (SELECT 1 FROM products parent WHERE parent.id=pr.group_parent_id260 AND parent.professional_id=p.id AND parent.available=1))
                AND (NOT EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=p.id AND lower(pc.name)=lower(pr.category))
                OR EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=p.id AND lower(pc.name)=lower(pr.category) AND pc.active=1))'''
            products=[]
            for row in conn.execute(product_sql,params):
                r=dict(row)
                if normalize(r['city']) != city_key or not is_vitrine_product(r):
                    continue
                if open_now=='1' and not shop_status(r)['open']:
                    continue
                item=browse_item(r,shop_status(r))
                if matches_product(item,tokens,item["promo"]):
                    products.append(item)
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
                item=r
                payload.append({'cart':{'id':r['id'],'name':r['name'],'price':item['price'],'max':r['max_quantity'],'slug':r['store_slug'],'store':r['store_name'],'options':item['requires_options']},'id':r['id'],'name':r['name'],'store_name':r['store_name'],'city':r['city'],
                    'price_cents':item['price'],
                    'image':image(r['image_filename']),'open':bool(status['open']),
                    'url':'/p/'+quote(r['store_slug'],safe='')+'/menu?produto='+str(r['id'])+'#produto-'+str(r['id'])})
            return JSONResponse({'products':payload,'stores':[{'name':r['display_name'],'city':r['city'],'open':bool(status['open']),
                'image':image(r['cover_filename'] or r['avatar_filename']),'url':'/p/'+quote(r['slug'],safe='')} for r,status in stores[:15]]},headers={'Cache-Control':'no-store'})
        finally:conn.close()

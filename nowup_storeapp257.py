"""Independent WhatsApp checkout, with shared server-side cart validation."""
import json
import re
import secrets
from datetime import datetime,timezone
from urllib.parse import urlsplit, parse_qs, quote
from fastapi import HTTPException, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse
from nowup_storeapp256 import store, HEADERS


def initialize(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS store_menu257 (professional_id INTEGER PRIMARY KEY REFERENCES professionals(id) ON DELETE CASCADE, whatsapp TEXT NOT NULL, mode TEXT NOT NULL DEFAULT 'both')")
    conn.execute("CREATE TABLE IF NOT EXISTS store_dispatch257 (order_id INTEGER PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE, response TEXT NOT NULL)")


def phone(raw):
    raw=(raw or '').strip()
    if len(raw)>300:raise HTTPException(400,'WhatsApp inválido')
    if '://' in raw:
        u=urlsplit(raw)
        if u.scheme!='https' or u.hostname not in ('wa.me','api.whatsapp.com','www.whatsapp.com') or u.username or u.password:
            raise HTTPException(400,'Use um número brasileiro ou um link oficial do WhatsApp')
        raw=u.path.strip('/') if u.hostname=='wa.me' else parse_qs(u.query).get('phone',[''])[0]
    if not re.fullmatch(r'[+()\d\s.-]+',raw):raise HTTPException(400,'WhatsApp inválido')
    digits=re.sub(r'\D','',raw)
    if len(digits) in (10,11):digits='55'+digits
    if len(digits) not in (12,13) or not digits.startswith('55') or digits[2:4]<'11' or digits[2:4]>'99' or len(set(digits))<3:
        raise HTTPException(400,'Informe o WhatsApp com DDD')
    return digits


def validate(g,conn,p,cart_json,fulfillment_type,payment_method,address,neighborhood,change_for):
    if not isinstance(cart_json,str) or len(cart_json.encode())>262144:raise HTTPException(400,'Carrinho inválido')
    if fulfillment_type not in ('delivery','pickup'):raise HTTPException(400,"Escolha entrega ou retirada.")
    if payment_method not in ('pix','cash','credit','debit','on_delivery'):raise HTTPException(400,"Escolha uma forma de pagamento válida.")
    if not g['shop_status'](p)["open"]: raise HTTPException(409,"Esta loja está fechada para pedidos.")
    try: raw_items=json.loads(cart_json)
    except Exception: raise HTTPException(400,"Carrinho inválido")
    if not isinstance(raw_items,list) or not raw_items: raise HTTPException(400,"Carrinho vazio")
    if len(raw_items)>50:
        raise HTTPException(400,"O carrinho permite até 50 itens diferentes. Divida o pedido.")
    clean_items=[]; subtotal=0; quantities255={}
    for raw in raw_items:
        try:
            if not isinstance(raw,dict) or type(raw.get("id")) is not int or type(raw.get("quantity",1)) is not int or raw["id"]<1 or not 1<=raw.get("quantity",1)<=99: raise ValueError()
            pid=raw["id"]; qty=raw.get("quantity",1); item_notes=str(raw.get("notes","")).strip()[:300]
        except (TypeError,ValueError,AttributeError):
            raise HTTPException(400,"Um item do carrinho é inválido. Revise o pedido.")
        product=conn.execute("SELECT pr.* FROM products pr WHERE pr.id=? AND pr.professional_id=? AND pr.available=1 AND (NOT EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category)) OR EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category) AND pc.active=1))",(pid,p["id"])).fetchone()
        if not product:
            raise HTTPException(400,"Um produto do carrinho ficou indisponível. Atualize o cardápio antes de enviar o pedido.")
        if product:
            quantities255[pid]=quantities255.get(pid,0)+qty
            if quantities255[pid]>min(99,max(1,product["max_quantity"] or 99)):
                raise HTTPException(400,"Quantidade acima do limite do produto. Revise o carrinho.")
            chosen=[]; extras=0
            try:chosen,extras=g['options_single158'](conn,pid,raw.get("options",[]))
            except HTTPException:raise
            utensils=raw.get("utensils",False)
            try:item_notes=g['validate_customization'](g['parse_config'](product["customization192"]),raw.get("customization",{}),item_notes,utensils)
            except HTTPException:raise
            try: g['validate_choices89'](conn,pid,chosen)
            except HTTPException: raise
            unit=(product["promo_price_cents"] if product["promo_price_cents"]>0 else product["price_cents"])+extras
            if unit<0:raise HTTPException(409,"Preço indisponível. Entre em contato com a loja.")
            clean_items.append((product,qty,item_notes,chosen,unit)); subtotal += unit*qty
    if not clean_items: raise HTTPException(400,"Nenhum produto disponível no carrinho")
    fulfillment_type="delivery" if fulfillment_type=="delivery" else "pickup"
    if fulfillment_type=="delivery" and not address.strip():
        raise HTTPException(400,"Informe o endereço para entrega")
    if fulfillment_type=="delivery" and not p["allows_delivery"]: raise HTTPException(400,"Esta loja não realiza entregas")
    if fulfillment_type=="pickup" and not p["allows_pickup"]: raise HTTPException(400,"Esta loja não permite retirada")
    if subtotal < (p["minimum_order_cents"] or 0): raise HTTPException(400,"O pedido não atingiu o valor mínimo")
    delivery_fee=0
    if fulfillment_type=="delivery":
        try: delivery_fee,neighborhood=g['delivery_quote89'](conn,p,neighborhood)
        except HTTPException: raise
    total=subtotal+delivery_fee
    payment_labels={"pix":"Pix","cash":"Dinheiro","credit":"Cartão de crédito","debit":"Cartão de débito","on_delivery":"Combinar no atendimento"}
    payment_method=payment_method if payment_method in payment_labels else "pix"
    change_for_cents=g['price_to_cents'](change_for) if payment_method=="cash" and change_for.strip() else 0
    if change_for_cents and change_for_cents<total:raise HTTPException(400,"O valor para troco deve cobrir o total do pedido.")
    return clean_items,subtotal,delivery_fee,neighborhood,total,change_for_cents


def money(cents):
    return 'R$ '+f'{cents/100:.2f}'.replace('.',',')


def install(g):
    app=g['app']
    @app.post('/painel/cardapio/whatsapp')
    def save_whatsapp257(request:Request,whatsapp:str=Form(''),mode:str=Form('both')):
        user=g['require_user'](request,'professional')
        if mode not in ('panel','whatsapp','both'):raise HTTPException(400,'Escolha um destino válido')
        number=phone(whatsapp) if whatsapp.strip() else '';conn=g['db']()
        try:
            p=g['require_premium_catalog'](conn,user['id'])
            conn.execute('INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,?,?) ON CONFLICT(professional_id) DO UPDATE SET whatsapp=excluded.whatsapp,mode=excluded.mode',(p['id'],number,mode))
            conn.commit()
        finally:conn.close()
        return RedirectResponse('/painel?ok=whatsapp#cardapio-independente',303)

    @app.post('/p/{slug}/menu/whatsapp')
    def whatsapp_checkout257(request:Request,slug:str,customer_name:str=Form(...),customer_phone:str=Form(''),cart_json:str=Form(...),fulfillment_type:str=Form('pickup'),payment_method:str=Form('pix'),address:str=Form(''),neighborhood:str=Form(''),address_reference:str=Form(''),change_for:str=Form(''),notes:str=Form(''),request_key:str=Form(...),save_address:str=Form('')):
        p=store(g,slug);user=g['require_user'](request,'customer')
        if user and user['id']==p['user_id']:raise HTTPException(403,'Você não pode fazer pedidos na sua própria loja.')
        name=str(user.get('name','')).strip()
        customer_phone=g['normalize_phone'](user.get('phone','') or customer_phone)
        if not customer_phone:raise HTTPException(400,'Informe um WhatsApp válido')
        if not 2<=len(name)<=120:raise HTTPException(400,'Informe seu nome (2 a 120 caracteres)')
        if len(address)>300 or len(neighborhood)>120 or len(address_reference)>220 or len(notes)>500:raise HTTPException(400,'Revise o tamanho dos dados do pedido')
        conn=g['db']()
        try:
            setting=conn.execute('SELECT whatsapp,mode FROM store_menu257 WHERE professional_id=?',(p['id'],)).fetchone()
            mode=setting['mode'] if setting else 'both'
            number=phone((setting['whatsapp'] if setting and setting['whatsapp'] else p['whatsapp'])) if mode!='panel' else ''
            from nowup_checkout229 import begin_checkout,remember_checkout
            identity=user['id'] if user and user['role']=='customer' else 0
            if not re.fullmatch(r'[A-Za-z0-9_-]{16,128}',request_key):raise HTTPException(400,'Atualize o carrinho antes de enviar.')
            existing,key,digest=begin_checkout(conn,identity,p['id'],request_key,{'cart':cart_json,'name':name,'phone':customer_phone,'fulfillment':fulfillment_type,'payment':payment_method,'address':address,'neighborhood':neighborhood,'reference':address_reference,'change':change_for,'notes':notes,'channel':'independent257'})
            if existing:
                row=conn.execute('SELECT d.response FROM store_dispatch257 d JOIN orders o ON o.id=d.order_id WHERE o.tracking_token=?',(existing,)).fetchone()
                if not row:raise HTTPException(409,'Pedido já registrado. Confira seu acompanhamento.')
                conn.rollback();conn.close()
                return JSONResponse(json.loads(row[0]),headers=HEADERS)
            lock=" FOR UPDATE" if getattr(conn,'dialect','sqlite')=='postgres' else ''
            fresh=conn.execute("SELECT p.* FROM professionals p JOIN users u ON u.id=p.user_id WHERE p.id=? AND p.blocked=0 AND p.admission_status='approved' AND p.plan_active IN ('cardapio','ambos') AND p.is_premium=1 AND p.offer_mode IN ('menu','catalog') AND u.is_active=1"+lock,(p['id'],)).fetchone()
            if not fresh:raise HTTPException(409,'Loja indisponível')
            p=dict(fresh)
            clean,subtotal,fee,area,total,change=validate(g,conn,p,cart_json,fulfillment_type,payment_method,address,neighborhood,change_for)
        except Exception:
            conn.close();raise
        lines=['Olá, '+p['display_name']+'! Quero fazer um pedido pelo cardápio.','Cliente: '+name,'WhatsApp do cliente: '+customer_phone,'']
        for product,qty,item_notes,chosen,unit in clean:
            lines.append(f"{qty}x {product['name']} — {money(unit*qty)}")
            for option in chosen:lines.append('  + '+option['name']+' ('+money(option['price_cents'])+')')
            if item_notes:lines.append('  Obs.: '+item_notes)
        lines+=['','Subtotal: '+money(subtotal),'Entrega: '+money(fee),'Total: '+money(total),'Recebimento: '+('Entrega' if fulfillment_type=='delivery' else 'Retirada no local')]
        if fulfillment_type=='delivery':lines+=['Endereço: '+address.strip(),'Bairro: '+area]
        if address_reference.strip():lines.append('Referência: '+address_reference.strip())
        labels={'pix':'Pix','cash':'Dinheiro','credit':'Cartão de crédito','debit':'Cartão de débito','on_delivery':'Combinar no atendimento'}
        lines.append('Pagamento: '+labels[payment_method])
        if change:lines.append('Troco para: '+money(change))
        if notes.strip():lines.append('Observação: '+notes.strip())
        lines+=['','Aguardando confirmação da loja.']
        message='\n'.join(lines)
        try:
            if len(message)>12000:raise HTTPException(400,'Pedido muito extenso para o WhatsApp. Divida os itens.')
            result={'prepared':True,'recorded':False,'mode':mode,'message':message,'total_cents':total}
            if mode!='whatsapp':
                created=datetime.now(timezone.utc).isoformat();token=secrets.token_urlsafe(24)
                cur=conn.execute("""INSERT INTO orders(professional_id,customer_id,customer_name,customer_phone,fulfillment_type,address,notes,status,total_cents,whatsapp_opened,created_at,updated_at,subtotal_cents,delivery_fee_cents,neighborhood,address_reference,change_for_cents,tracking_token)
                    VALUES(?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,?,?,?)""",(p['id'],identity or None,name,customer_phone,fulfillment_type,address.strip(),notes.strip(),'new',total,created,created,subtotal,fee,area,address_reference.strip(),change,token))
                oid=cur.lastrowid;code=f'NU-{oid:06d}'
                conn.execute("UPDATE orders SET payment_method=?,order_code=?,order_origin='external' WHERE id=?",(payment_method,code,oid))
                conn.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(oid,'new',created))
                for product,qty,item_notes,chosen,unit in clean:
                    item=conn.execute('INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price_cents,notes) VALUES(?,?,?,?,?,?)',(oid,product['id'],product['name'],qty,unit,item_notes))
                    for option in chosen:conn.execute('INSERT INTO order_item_options(order_item_id,option_id,option_name,price_cents) VALUES(?,?,?,?)',(item.lastrowid,option['id'],option['name'],option['price_cents']))
                conn.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(p['user_id'],'Novo pedido no NowUp',code+' — '+name,'/painel#pedido-'+str(oid),created))
                g['nowup_push75'].enqueue_on_connection(conn,p['user_id'],oid)
                if fulfillment_type=='delivery' and save_address:
                    conn.execute("UPDATE users SET address=?,neighborhood=?,address_reference=? WHERE id=? AND role='customer'",(address.strip(),area,address_reference.strip(),identity))
                remember_checkout(conn,identity,p['id'],key,digest,oid,created)
                result.update(recorded=True,redirect='/p/'+slug+'/pedido/'+token,order_code=code)
                result['message']='Pedido '+code+' — registrado no painel (não duplicar).\n'+message
            if mode!='panel':result['whatsapp_url']='https://wa.me/'+number+'?text='+quote(result['message'],safe='')
            if result['recorded']:
                conn.execute('INSERT INTO store_dispatch257(order_id,response) VALUES(?,?)',(oid,json.dumps(result,ensure_ascii=False)))
                conn.commit()
            else:conn.rollback()
            return JSONResponse(result,headers=HEADERS)
        finally:conn.close()

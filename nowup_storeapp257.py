from nowup_combos303 import current_price
"""Independent WhatsApp checkout, with shared server-side cart validation."""
import json
from nowup_combo_pack305 import build_pack
from nowup_combo_units364 import validate_units
import re
import secrets
from datetime import datetime,timezone
from urllib.parse import urlsplit, parse_qs, quote
from fastapi import HTTPException, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse
from nowup_storeapp256 import store, HEADERS


def initialize(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS store_menu257 (professional_id INTEGER PRIMARY KEY REFERENCES professionals(id) ON DELETE CASCADE, whatsapp TEXT NOT NULL, mode TEXT NOT NULL DEFAULT 'both')")
    conn.execute("CREATE TABLE IF NOT EXISTS store_order_settings377 (professional_id INTEGER PRIMARY KEY REFERENCES professionals(id) ON DELETE CASCADE, message TEXT NOT NULL DEFAULT '')")
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


def validate(g,conn,p,cart_json,fulfillment_type,payment_method,address,neighborhood,change_for,scheduled_for380=""):
    if not isinstance(cart_json,str) or len(cart_json.encode())>262144:raise HTTPException(400,'Carrinho inválido')
    if fulfillment_type not in ('delivery','pickup'):raise HTTPException(400,"Escolha entrega ou retirada.")
    if payment_method not in ('pix','cash','credit','debit','on_delivery'):raise HTTPException(400,"Escolha uma forma de pagamento válida.")
    from nowup_scheduling380 import validate as validate_schedule
    validate_schedule(p,scheduled_for380)
    if not scheduled_for380 and not g['shop_status'](p)["open"]: raise HTTPException(409,"Esta loja está fechada para pedidos.")
    try: raw_items=json.loads(cart_json)
    except Exception: raise HTTPException(400,"Carrinho inválido")
    if not isinstance(raw_items,list) or not raw_items: raise HTTPException(400,"Carrinho vazio")
    if len(raw_items)>50:
        raise HTTPException(400,"O carrinho permite até 50 itens diferentes. Divida o pedido.")
    clean_items=[]; subtotal=0; quantities255={}; fashion_stock389={}
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
            product=dict(product)
            user_notes305=item_notes
            quantities255[pid]=quantities255.get(pid,0)+qty
            if product.get('sold_by_weight370') and quantities255[pid]>1:raise HTTPException(400,'Escolha o peso total em um único item por produto.')
            if quantities255[pid]>min(99,max(1,product["max_quantity"] or 99)):
                raise HTTPException(400,"Quantidade acima do limite do produto. Revise o carrinho.")
            chosen=[]; extras=0
            try:chosen,extras=g['options_single158'](conn,pid,raw.get("options",[]))
            except HTTPException:raise
            utensils=raw.get("utensils",False)
            try:item_notes=g['validate_customization'](g['parse_config'](product["customization192"]),raw.get("customization",{}),item_notes,utensils)
            except HTTPException:raise
            from nowup_fashion_stock389 import validate as validate_stock389
            if dict(p).get('business_type')=='fashion':validate_stock389(product,raw.get('customization',{}),qty,fashion_stock389)
            combo_base_details365=item_notes
            combo_units364=[];combo_chosen364=[];combo_price364=0
            unit_combo365=bool(product.get('is_combo256') or g['parse_config'](product['customization192']).get('meal_combo324'))
            if unit_combo365:
                combo_units364,combo_chosen364,combo_price364=validate_units(g,conn,p['id'],g['parse_config'](product['customization192']),raw.get('customization',{}))
                if combo_units364:item_notes=(item_notes+' · ' if item_notes else '')+' · '.join(unit['name']+' '+str(unit['position'])+': '+(unit['notes'] or 'Completo') for unit in combo_units364)
            elif raw.get('customization',{}).get('units364'):raise HTTPException(400,'Este produto não é um combo.')
            product['combo_pack305']=build_pack(g['parse_config'](product['customization192']),raw.get('customization',{}),user_notes305,combo_units364,combo_base_details365 if not product.get('is_combo256') else '') if unit_combo365 else ''
            try: g['validate_choices89'](conn,pid,chosen)
            except HTTPException: raise
            chosen.extend(combo_chosen364)
            unit=(current_price(product))+extras+combo_price364
            from nowup_weight370 import apply_line
            weighted370=apply_line(product,raw,qty,item_notes,chosen)
            if weighted370:unit,item_notes=weighted370
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
    def save_whatsapp257(request:Request,whatsapp:str=Form(''),mode:str=Form('both'),order_message:str=Form('')):
        user=g['require_user'](request,'professional')
        if mode not in ('panel','whatsapp','both'):raise HTTPException(400,'Escolha um destino válido')
        number=phone(whatsapp) if whatsapp.strip() else '';conn=g['db']()
        try:
            p=g['require_premium_catalog'](conn,user['id'])
            if p['plan_active'] not in ('cardapio','completo'):raise HTTPException(403,'Seu plano recebe pedidos somente dentro do NowUp')
            conn.execute('INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,?,?) ON CONFLICT(professional_id) DO UPDATE SET whatsapp=excluded.whatsapp,mode=excluded.mode',(p['id'],number,mode))
            if len(order_message)>300:raise HTTPException(400,'Mensagem deve ter até 300 caracteres')
            conn.execute('INSERT INTO store_order_settings377(professional_id,message) VALUES(?,?) ON CONFLICT(professional_id) DO UPDATE SET message=excluded.message',(p['id'],order_message.strip()))
            conn.commit()
        finally:conn.close()
        return RedirectResponse('/painel?ok=whatsapp#cardapio-independente',303)

    @app.post('/p/{slug}/menu/whatsapp')
    def whatsapp_checkout257(request:Request,slug:str,customer_name:str=Form(...),customer_phone:str=Form(''),cart_json:str=Form(...),fulfillment_type:str=Form('pickup'),payment_method:str=Form('pix'),address:str=Form(''),neighborhood:str=Form(''),address_reference:str=Form(''),change_for:str=Form(''),notes:str=Form(''),request_key:str=Form(...),save_address:str=Form(''),scheduled_for380:str=Form('')):
        p=store(g,slug);user=g['require_user'](request,'customer')
        fashion385=dict(p).get('business_type')=='fashion'
        if fashion385 and dict(p).get('is_demo') and p['slug'] in ('nowup-moda-demonstracao','nowup-moda-modelo'):
            raise HTTPException(409,'Loja de demonstração: produtos e preços ilustrativos, sem pedidos reais.')
        if fashion385:payment_method='on_delivery'
        if user and user['id']==p['user_id']:raise HTTPException(403,'Você não pode fazer pedidos na sua própria loja.')
        name=str(user.get('name','')).strip()
        customer_phone=g['normalize_phone'](user.get('phone','') or customer_phone)
        if not customer_phone:raise HTTPException(400,'Informe um WhatsApp válido')
        if not 2<=len(name)<=120:raise HTTPException(400,'Informe seu nome (2 a 120 caracteres)')
        if len(address)>300 or len(neighborhood)>120 or len(address_reference)>220 or len(notes)>500:raise HTTPException(400,'Revise o tamanho dos dados do pedido')
        conn=g['db']()
        try:
            setting=conn.execute('SELECT whatsapp,mode FROM store_menu257 WHERE professional_id=?',(p['id'],)).fetchone()
            mode='whatsapp' if fashion385 else (setting['mode'] if setting else 'whatsapp')
            if mode=='both':mode='whatsapp'
            number=phone((setting['whatsapp'] if setting and setting['whatsapp'] else p['whatsapp'])) if mode!='panel' else ''
            from nowup_checkout229 import begin_checkout,remember_checkout
            identity=user['id'] if user and user['role']=='customer' else 0
            if not re.fullmatch(r'[A-Za-z0-9_-]{16,128}',request_key):raise HTTPException(400,'Atualize o carrinho antes de enviar.')
            existing,key,digest=begin_checkout(conn,identity,p['id'],request_key,{'cart':cart_json,'name':name,'phone':customer_phone,'fulfillment':fulfillment_type,'payment':payment_method,'address':address,'neighborhood':neighborhood,'reference':address_reference,'change':change_for,'scheduled_for380':scheduled_for380,'notes':notes,'channel':'independent257'})
            if existing:
                row=conn.execute('SELECT d.response FROM store_dispatch257 d JOIN orders o ON o.id=d.order_id WHERE o.tracking_token=?',(existing,)).fetchone()
                if not row:raise HTTPException(409,'Pedido já registrado. Confira seu acompanhamento.')
                conn.rollback();conn.close()
                return JSONResponse(json.loads(row[0]),headers=HEADERS)
            lock=" FOR UPDATE" if getattr(conn,'dialect','sqlite')=='postgres' else ''
            fresh=conn.execute("SELECT p.* FROM professionals p JOIN users u ON u.id=p.user_id WHERE p.id=? AND p.blocked=0 AND p.admission_status='approved' AND p.plan_active IN ('cardapio','completo') AND p.is_premium=1 AND p.offer_mode IN ('menu','catalog') AND u.is_active=1"+lock,(p['id'],)).fetchone()
            if not fresh:raise HTTPException(409,'Loja indisponível')
            p=dict(fresh)
            clean,subtotal,fee,area,total,change=validate(g,conn,p,cart_json,fulfillment_type,payment_method,address,neighborhood,change_for,scheduled_for380)
        except Exception:
            conn.close();raise
        from nowup_whatsapp_receipt import build as build_receipt
        receipt,message=build_receipt(p,name,customer_phone,clean,subtotal,fee,total,
            fulfillment_type,address,area,address_reference,payment_method,change,notes)
        try:
            if len(message)>12000:raise HTTPException(400,'Pedido muito extenso para o WhatsApp. Divida os itens.')
            result={'prepared':True,'recorded':False,'mode':mode,'message':message,'total_cents':total,'receipt':receipt}
            status376='new'
            created=datetime.now(timezone.utc).isoformat();token=secrets.token_urlsafe(24)
            cur=conn.execute("""INSERT INTO orders(professional_id,customer_id,customer_name,customer_phone,fulfillment_type,address,notes,status,total_cents,whatsapp_opened,created_at,updated_at,subtotal_cents,delivery_fee_cents,neighborhood,address_reference,change_for_cents,tracking_token)
                VALUES(?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,?,?,?)""",(p['id'],identity or None,name,customer_phone,fulfillment_type,address.strip(),notes.strip(),status376,total,created,created,subtotal,fee,area,address_reference.strip(),change,token))
            oid=cur.lastrowid;code=f'NU-{oid:06d}'
            from nowup_scheduling380 import save as save_schedule
            scheduled380=save_schedule(conn,oid,p,scheduled_for380)
            conn.execute("UPDATE orders SET payment_method=?,order_code=?,order_origin=? WHERE id=?",(payment_method,code,'external' if mode=='whatsapp' else 'nowup',oid))
            conn.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(oid,status376,created))
            for product,qty,item_notes,chosen,unit in clean:
                item=conn.execute('INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price_cents,notes,combo_pack305) VALUES(?,?,?,?,?,?,?)',(oid,product['id'],product['name'],qty,unit,item_notes,product.get('combo_pack305','')))
                from nowup_weight370 import snapshot
                snapshot(conn,item.lastrowid,product)
                for option in chosen:conn.execute('INSERT INTO order_item_options(order_item_id,option_id,option_name,price_cents) VALUES(?,?,?,?)',(item.lastrowid,option['id'],option['name'],option['price_cents']))
            if mode=='panel':
                conn.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(p['user_id'],'Novo pedido no NowUp',code+' — '+name,'/painel#pedido-'+str(oid),created))
                g['nowup_push75'].enqueue_on_connection(conn,p['user_id'],oid)
            if identity:
                received=conn.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(identity,'Pedido enviado à loja',code+' enviado. Aguardando aceite da loja.','/pedido/'+token,created))
                g['nowup_alerts112'].enqueue(conn,identity,received.lastrowid,{'title':'Pedido enviado à loja','body':code+' enviado. Aguardando aceite da loja.','url':'/pedido/'+token,'tag':'nowup-recebido-'+str(oid)})
            if fulfillment_type=='delivery' and save_address:
                conn.execute("UPDATE users SET address=?,neighborhood=?,address_reference=? WHERE id=? AND role='customer'",(address.strip(),area,address_reference.strip(),identity))
            remember_checkout(conn,identity,p['id'],key,digest,oid,created)
            result.update(recorded=True,whatsapp_only=(mode=='whatsapp'),redirect='/p/'+slug+'/pedido/'+token,order_code=code)
            result['receipt']['order_code']=code
            result['review_required']=True
            result['whatsapp_only']=False
            result['receipt']['status']='Aguardando revisão do lojista — pagamento após confirmação'
            from nowup_menu_origin355 import email_origin
            base=email_origin() or str(request.base_url).rstrip('/')
            result['order_url']=base+result['redirect']
            management_base=g['os'].getenv('NOWUP_PUBLIC_ORIGIN','').strip().rstrip('/') or g['os'].getenv('NOWUP_BASE_URL','').strip().rstrip('/') or str(request.base_url).rstrip('/')
            result['merchant_url']=management_base+'/pedido/'+token
            from zoneinfo import ZoneInfo
            hour=datetime.now(ZoneInfo('America/Sao_Paulo')).hour
            greeting='bom dia' if 5<=hour<12 else 'boa tarde' if hour<18 else 'boa noite'
            saved_message=conn.execute('SELECT message FROM store_order_settings377 WHERE professional_id=?',(p['id'],)).fetchone()
            template=(saved_message['message'] if saved_message else '') or 'Olá, {saudacao}! Fiz o pedido {pedido} pelo NowUp. Pode revisar e confirmar, por favor?'
            for field,value in {'saudacao':greeting,'pedido':code,'loja':p['display_name'],'total':money(total)}.items():
                template=template.replace('{'+field+'}',value)
            if scheduled380:template+='\nHorário solicitado para hoje: '+datetime.fromisoformat(scheduled380).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%H:%M')+' (aguardando confirmação)'
            result['message']=template+'\nPedido '+code+' — revisão pelo lojista:\n'+result['merchant_url']
            if fashion385:
                result['message']='Olá! Quero confirmar a disponibilidade e separar estas peças para retirada ou entrega.\n\n'+message+'\nPagamento a combinar pelo WhatsApp.'
            result['receipt']['order_url']=result['order_url']
            if mode!='panel':result['whatsapp_url']='https://wa.me/'+number+'?text='+quote(result['message'],safe='')
            conn.execute('INSERT INTO store_dispatch257(order_id,response) VALUES(?,?)',(oid,json.dumps(result,ensure_ascii=False)))
            conn.commit()
            return JSONResponse(result,headers=HEADERS)
        finally:conn.close()


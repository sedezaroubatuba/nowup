"""Server-owned checkout amounts and manual settlement of static Pix orders."""
import json
import re
from fastapi import HTTPException, Request

WAITING = 'awaiting_payment'
WAITING_LABEL = 'Aguardando Confirmação de Pagamento'
MAX_CENTS = 999999999999
ITEM_KEYS = {'id','quantity','notes','options','utensils','customization','weight_grams370'}
FORM_KEYS = {'customer_name','customer_phone','cart_json','fulfillment_type','payment_method','address',
    'neighborhood','address_reference','change_for','notes','request_key','save_address','scheduled_for380',
    'basket_key391','order_channel','store_id','professional_id','csrf_token'}
MONEY_KEYS = {'price','unitprice','unitpricecents','pricecents','subtotal','subtotalcents','total','totalcents',
    'deliveryfee','deliveryfeecents','fee','feecents','discount','discountcents','amount','amountcents',
    'pixkey','pixpayload','qrcode','paymentconfirmed','paymentchecked'}


def reject_money(value, depth=0):
    if depth > 20: raise HTTPException(400, 'Escolhas do pedido muito complexas.')
    if isinstance(value, dict):
        for key, child in value.items():
            if re.sub(r'[^a-z0-9]', '', str(key).lower()) in MONEY_KEYS:
                raise HTTPException(400, 'Preço, desconto, frete, total e dados Pix são definidos exclusivamente pelo servidor.')
            reject_money(child, depth + 1)
    elif isinstance(value, list):
        for child in value: reject_money(child, depth + 1)


def validate_cart(raw_items):
    if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 50: raise HTTPException(400, 'Carrinho inválido: use de 1 a 50 itens.')
    for item in raw_items:
        if not isinstance(item, dict) or set(item) - ITEM_KEYS:
            raise HTTPException(400, 'O carrinho deve conter somente IDs, quantidades e escolhas do pedido, sem valores.')
    for item in raw_items:
        if not isinstance(item.get('customization',{}),dict) or not isinstance(item.get('options',[]),list):
            raise HTTPException(400, 'Escolhas do produto inválidas.')
    reject_money(raw_items)


async def checkout_fields(request: Request):
    form = await request.form()
    if set(form) - FORM_KEYS:
        raise HTTPException(400, 'Campo não permitido no checkout. Os valores são calculados pelo servidor.')
    for name in FORM_KEYS:
        if len(form.getlist(name)) > 1: raise HTTPException(400, 'Campo duplicado no checkout.')
    request.state.checkout_store422 = {name: str(form[name]) for name in ('store_id','professional_id') if name in form}
    cart = str(form.get('cart_json','[]'))
    if len(cart.encode()) > 262144: raise HTTPException(400, 'Carrinho muito extenso.')
    try: raw = json.loads(cart)
    except (ValueError, TypeError, RecursionError): raise HTTPException(400, 'Carrinho inválido.')
    validate_cart(raw)


def check_store(request, store_id):
    for value in getattr(request.state, 'checkout_store422', {}).values():
        if not 1 <= len(value) <= 19 or not value.isascii() or not value.isdigit() or int(value) != store_id:
            raise HTTPException(400, 'A loja informada não corresponde ao cardápio.')


def initial_status(method): return WAITING if method == 'pix' else 'new'


def check_totals(subtotal, fee, total):
    if any(type(v) is not int or not 0 <= v <= MAX_CENTS for v in (subtotal, fee, total)) or total != subtotal + fee or total<=0:
        raise HTTPException(409, 'Valores do pedido indisponíveis. Atualize o cardápio.')


def require_pix_received(c, order_id, target):
    if target not in {'preparing','ready','out_for_delivery','completed'}: return
    order = c.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
    if order and order['payment_method'] == 'pix':
        from nowup_notinha401 import payment_checked
        if not payment_checked(c, order):
            raise HTTPException(409, 'Confirme o recebimento do Pix no banco antes de iniciar o preparo ou avançar este pedido.')

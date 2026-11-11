"""Small authenticated order fragment for the merchant's live order notice."""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse


def install(g):
    def detail(request: Request, order_id: int):
        user=g['require_user'](request,'professional')
        with g['db']() as c:
            order=c.execute('''SELECT o.*,p.display_name,p.slug FROM orders o
                JOIN professionals p ON p.id=o.professional_id WHERE o.id=? AND p.user_id=?''',
                (order_id,user['id'])).fetchone()
            if not order:raise HTTPException(404,'Pedido não encontrado')
            items=c.execute('SELECT * FROM order_items WHERE order_id=? ORDER BY id',(order_id,)).fetchall()
            options={}
            for option in c.execute('''SELECT op.* FROM order_item_options op JOIN order_items i
                    ON i.id=op.order_item_id WHERE i.order_id=? ORDER BY op.id''',(order_id,)):
                options.setdefault(option['order_item_id'],[]).append(option)
            paid=g['nowup_notinha401'].payment_checked(c,order)
            return g['templates'].TemplateResponse('merchant_order407.html',{
                'request':request,'user':user,'order':order,'items':items,'options':options,
                'order_items_by_order':{order_id:items},'order_item_options':options,
                'review_customer':False,'order_link377':False,'payment_checked':paid,
                'status_labels':g['ORDER_STATUS_LABELS']},headers={'Cache-Control':'private, no-store'})

    def status_response(request, order_id, status):
        payload={'id':order_id,'status':status}
        if request.headers.get('x-nowup-order-detail')=='1':
            payload['html407']=detail(request,order_id).body.decode('utf-8')
        return JSONResponse(payload,headers={'Cache-Control':'private, no-store'})

    g['order_status_response407']=status_response
    g['app'].add_api_route('/painel/pedidos/{order_id}/detalhes407',detail,methods=['GET'],response_class=g['HTMLResponse'])

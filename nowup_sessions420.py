"""Foreground session checks reveal no credentials and never revive revoked sessions."""
from fastapi import Request
from fastapi.responses import JSONResponse

HEADERS={'Cache-Control':'private, no-store','Vary':'Cookie'}

def install(g):
    def payload(request,store_id=0):
        user=g['current_user'](request)
        valid=bool(user and (not store_id or (user['role']=='customer' and user.get('customer_store345')==store_id)))
        return JSONResponse({'authenticated':valid,'role':user['role'] if valid else None,'user_id':user['id'] if valid else None},headers=HEADERS)
    @g['app'].get('/sessao420')
    def main_session(request:Request):return payload(request)
    @g['app'].get('/p/{slug}/sessao420')
    def store_session(request:Request,slug:str):
        from nowup_storeapp256 import store
        p=store(g,slug);request.state.store_app256=p
        return payload(request,p['id'])

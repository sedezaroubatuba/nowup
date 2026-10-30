"""Friendly browser validation pages; APIs retain their existing JSON contracts."""
from html import escape
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException

def page(status, message):
    title='Confira antes de continuar' if status in (400,409,422) else 'Não foi possível continuar'
    return HTMLResponse('''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NowUp • Confira os dados</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100dvh;display:grid;place-items:center;padding:24px;background:#f7f3fc;color:#302142;font-family:system-ui,sans-serif}.card{width:min(100%,460px);padding:30px;background:white;border:1px solid #e8dcf5;border-radius:24px;box-shadow:0 16px 55px #4d257014}.brand{font-size:25px;font-weight:850;color:#793bc6}.icon{display:grid;place-items:center;width:54px;height:54px;background:#f3eaff;color:#793bc6;border-radius:18px;font-size:30px;margin:24px 0 18px}h1{font-size:23px;line-height:1.2}p{line-height:1.6;color:#62556f}button,a{display:block;width:100%;border-radius:12px;padding:14px;font:inherit;text-align:center;text-decoration:none;cursor:pointer}button{border:0;background:#793bc6;color:white;font-weight:700;margin-top:24px}a{color:#793bc6;margin-top:6px}button:focus-visible,a:focus-visible{outline:3px solid #b58cde;outline-offset:3px}
</style></head><body><main class="card"><div class="brand">NowUp</div><div class="icon" aria-hidden="true">!</div><h1>'''+title+'''</h1><p role="alert">'''+escape(message)+'''</p><button type="button" onclick="if(history.length>1){history.back()}else{location.href='/'}">Voltar e conferir</button><a href="/">Ir para o início</a></main></body></html>''',status_code=status,headers={'Cache-Control':'no-store'})

def browser(request):
    accept=request.headers.get('accept','').lower()
    return 'text/html' in accept and 'application/json' not in accept and not request.url.path.startswith('/api/')

def install(app):
    @app.exception_handler(HTTPException)
    async def friendly_http(request,exc):
        if not browser(request) or not 400<=exc.status_code<500:
            return await http_exception_handler(request,exc)
        message=exc.detail if isinstance(exc.detail,str) and exc.detail not in ('Not Found','Forbidden','Unauthorized','Bad Request') else {
            401:'Entre na sua conta para continuar.',403:'Esta ação não está disponível para sua conta.',404:'Não encontramos esta página. Volte e confira o endereço.'}.get(exc.status_code,'Confira os dados informados e tente novamente.')
        response=page(exc.status_code,message)
        if exc.headers:response.headers.update(exc.headers)
        return response
    @app.exception_handler(RequestValidationError)
    async def friendly_validation(request,exc):
        if not browser(request):return await request_validation_exception_handler(request,exc)
        return page(422,'Algum campo está vazio ou tem um valor inválido. Volte ao cadastro e confira os dados.')

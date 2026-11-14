"""Optional dedicated origin for store catalogues; dormant until DNS/TLS is ready."""
import os
from urllib.parse import quote, urlsplit

from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool


def menu_origin():
    value = os.getenv('NOWUP_MENU_ORIGIN', '').strip().rstrip('/')
    if not value:
        return ''
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.path or parsed.query or parsed.fragment
                or any(ord(c) <= 32 or c == '\\' for c in value)):
            raise ValueError()
        parsed.port
        from nowup_runtime238 import origin_tuple
        for key in ('NOWUP_PUBLIC_ORIGIN', 'NOWUP_BASE_URL'):
            if origin_tuple(value) == origin_tuple(os.getenv(key, '')):
                raise ValueError()
    except ValueError:
        raise ValueError('NOWUP_MENU_ORIGIN deve ser uma origem HTTPS diferente da vitrine') from None
    return value


def is_menu_host(request):
    origin = menu_origin()
    if not origin:
        return False
    from nowup_runtime238 import origin_tuple
    base = request.base_url.replace(scheme='https') if os.getenv('NOWUP_HTTPS') == '1' else request.base_url
    return origin_tuple(origin) == origin_tuple(str(base))


def external_menu(request, slug):
    base = menu_origin()
    if not base:
        base = str(request.base_url.replace(scheme='https') if os.getenv('NOWUP_HTTPS') == '1' else request.base_url).rstrip('/')
    return base + '/p/' + quote(slug, safe='') + '/cardapio'


def email_origin():
    return menu_origin() or os.getenv('NOWUP_BASE_URL', '').strip().rstrip('/')


def install(g):
    # Fail early on invalid configuration, before any links are advertised.
    menu_origin()
    g['templates'].env.globals['external_menu355'] = external_menu
    g['templates'].env.globals['menu_origin355'] = menu_origin

    @g['app'].middleware('http')
    async def catalogue_origin355(request, call_next):
        origin = menu_origin()
        if not origin:
            return await call_next(request)
        parts = request.url.path.split('/')
        store_path = len(parts) >= 3 and parts[1] == 'p'
        if is_menu_host(request):
            # Never install or navigate into the marketplace on this origin.
            if not store_path:
                if request.url.path.startswith(('/static/', '/uploads/')) or request.url.path == '/health':
                    if request.url.path in ('/static/nowup.webmanifest', '/static/nowup-lojista.webmanifest'):
                        return JSONResponse({'detail': 'Use o aplicativo da loja'}, status_code=404)
                    return await call_next(request)
                return JSONResponse({'detail': 'Abra o link exclusivo da loja'}, status_code=404)
            from nowup_storeapp256 import store
            try:
                request.state.store_app256 = await run_in_threadpool(store, g, parts[2])
            except HTTPException as exc:
                return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)
        elif request.method in ('GET', 'HEAD') and store_path and request.url.path.rstrip('/').endswith(('/menu','/cardapio')):
            from nowup_storeapp256 import store
            try:
                p = await run_in_threadpool(store, g, parts[2])
            except HTTPException:
                p = None
            explicit = request.url.path.rstrip('/').endswith('/cardapio') or request.query_params.get('loja') == '1' or request.query_params.get('origem') == 'externo'
            if p and (p['plan_active'] == 'cardapio' or explicit):
                # Only navigation is redirected: never replay a form or checkout.
                url = origin + request.url.path
                if request.url.query:
                    url += '?' + request.url.query
                return RedirectResponse(url, 307, headers={'Cache-Control': 'private, no-store'})
        return await call_next(request)

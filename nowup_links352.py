"""External links are an explicit entitlement of standalone catalogue plans."""
from urllib.parse import urlsplit
from fastapi import HTTPException, Request, Form
from fastapi.responses import RedirectResponse

LINK_PLANS = ('cardapio', 'completo')


def clean_url(value, instagram=False):
    value = (value or '').strip()
    if not value:
        return ''
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        valid = (len(value) <= 500 and parsed.scheme == 'https' and host
                 and not parsed.username and not parsed.password
                 and not any(ord(char) <= 32 or char == '\\' for char in value))
        if instagram:
            valid = valid and host.lower() in ('instagram.com', 'www.instagram.com')
        if not valid:
            raise ValueError()
        parsed.port
    except ValueError:
        raise HTTPException(400, 'Informe um link HTTPS válido' + (' do Instagram' if instagram else ' do site'))
    return value


def public_links(p):
    result = dict(p)
    for key in ('instagram_url', 'facebook_url', 'website_url', 'external_url', 'menu_url'):
        result[key] = ''
    if p['plan_active'] in LINK_PLANS:
        for key in ('instagram_url', 'website_url'):
            try:
                result[key] = clean_url(p[key], instagram=key == 'instagram_url')
            except HTTPException:
                pass
    return result


def destination(g, slug, network):
    from nowup_storeapp256 import store
    p = store(g, slug)
    key = {'instagram': 'instagram_url', 'site': 'website_url'}.get(network)
    if not key:
        raise HTTPException(404, 'Link não disponível')
    url = public_links(p)[key]
    if not url:
        raise HTTPException(404, 'Link não configurado')
    return RedirectResponse(url, 303, headers={'Cache-Control': 'private, no-store'})


def install(g):
    @g['app'].post('/painel/cardapio/links352')
    def save_links352(request: Request, instagram_url: str = Form(''), website_url: str = Form('')):
        user = g['require_user'](request, 'professional')
        with g['db']() as conn:
            p = g['require_premium_catalog'](conn, user['id'])
            if p['plan_active'] not in LINK_PLANS:
                raise HTTPException(403, 'Seu plano recebe pedidos somente dentro do NowUp')
            instagram = clean_url(instagram_url, instagram=True)
            site = clean_url(website_url)
            conn.execute('UPDATE professionals SET instagram_url=?,website_url=? WHERE id=?', (instagram, site, p['id']))
            conn.commit()
        return RedirectResponse('/painel?ok=links#cardapio-independente', 303)

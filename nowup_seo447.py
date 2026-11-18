"""Public search metadata and noindex protection for private NowUp areas.

Noindex is a discoverability hint, NOT access control. Authentication remains
mandatory on Super ADM and other private pages.
"""
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response

SITE_URL = "https://nowupbrasil.com"
PRIVATE_PATHS = (
    "/admin", "/painel", "/cliente", "/pedido", "/entrar",
    "/cadastro", "/recuperar-senha", "/redefinir-senha",
    "/api", "/sair", "/verificar",
)
router = APIRouter()


def is_private_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in PRIVATE_PATHS)


@router.get("/robots.txt", include_in_schema=False)
def robots_txt():
    # Let crawlers read X-Robots-Tag from private routes; disallowing those
    # paths here could prevent them from seeing their noindex response.
    return PlainTextResponse(
        "User-agent: *\nAllow: /\nSitemap: " + SITE_URL + "/sitemap.xml\n",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    # Only public, stable entry points. Never include Super ADM, credentials,
    # merchant panels, private orders, or per-user URLs.
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           '<url><loc>' + SITE_URL + '/</loc></url>'
           '<url><loc>' + SITE_URL + '/profissionais</loc></url>'
           '</urlset>')
    return Response(xml, media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})


def install(app):
    app.include_router(router)

    @app.middleware("http")
    async def private_search_exclusion(request: Request, call_next):
        response = await call_next(request)
        if is_private_path(request.url.path):
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response

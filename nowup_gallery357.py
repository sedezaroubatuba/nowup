"""Read-only ingredient library. Imports use existing merchant-scoped photo forms."""
import io
import json
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, Response
from PIL import Image

ROOT = Path(__file__).resolve().parent / 'static' / 'ingredient-gallery357'


@lru_cache(maxsize=1)
def catalog():
    return json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=128)
def photo(key):
    item = next((row for row in catalog() if row['id'] == key), None)
    if item is None:
        raise HTTPException(404, 'Imagem da galeria não encontrada.')
    # Atlas filenames and cell coordinates come only from the packaged catalog.
    with Image.open(ROOT / item['atlas']) as source:
        col = item['cell'] % item['columns']
        row = item['cell'] // item['columns']
        box = (round(col * source.width / item['columns']),
               round(row * source.height / item['rows']),
               round((col + 1) * source.width / item['columns']),
               round((row + 1) * source.height / item['rows']))
        image = source.crop(box).convert('RGB').resize((1000, 1000), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, 'JPEG', quality=86, optimize=True)
    return output.getvalue()


def install(g):
    @g['app'].get('/painel/galeria-nowup/ingredientes')
    def ingredients(request: Request):
        user = g['require_user'](request, 'professional')
        conn = g['db']()
        try:
            g['require_premium_catalog'](conn, user['id'])
        finally:
            conn.close()
        return JSONResponse([{'id': row['id'], 'name': row['name'],
                              'category': row['category'],
                              'photo': '/galeria-nowup/ingredientes/' + row['id'] + '.jpg'}
                             for row in catalog()])

    @g['app'].get('/painel/galeria-nowup/itens-da-loja')
    def store_ingredients(request: Request):
        user = g['require_user'](request, 'professional')
        conn = g['db']()
        try:
            store = g['require_premium_catalog'](conn, user['id'])
            return JSONResponse(g['nowup_ingredients320'].catalog(conn, store['id']))
        finally:
            conn.close()

    @g['app'].get('/galeria-nowup/ingredientes/{key}.jpg')
    def ingredient_photo(key: str):
        return Response(photo(key), media_type='image/jpeg', headers={
            'Cache-Control': 'public, max-age=86400', 'X-Content-Type-Options': 'nosniff'})

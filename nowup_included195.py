"""Private store registries for included sides and combo drinks."""
import json
import sqlite3
from fastapi import Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from nowup_custom192 import parse_config, integer, save_config


def initialize(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS included_choices195(
        id INTEGER PRIMARY KEY, professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
        kind TEXT NOT NULL CHECK(kind IN ('side','drink')),name TEXT NOT NULL,
        available INTEGER NOT NULL DEFAULT 1)''')
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS included_name195 ON included_choices195(professional_id,kind,lower(name))')


def catalog(conn, professional_id):
    return [dict(row) for row in conn.execute('SELECT * FROM included_choices195 WHERE professional_id=? ORDER BY kind,name,id', (professional_id,))]


def resolve(conn, professional_id, config):
    meta = config.get('included195')
    if meta is None:
        return config
    if not isinstance(meta, dict) or not isinstance(meta.get('is_combo', False), bool) or not isinstance(meta.get('side_required', False), bool):
        raise HTTPException(400, 'Configuração do combo inválida.')
    groups = [g for g in config['groups'] if g['id'] not in ('side195', 'drink195')]
    clean = {'is_combo': meta.get('is_combo', False), 'side_required': meta.get('side_required', False)}
    for kind, key in [('side', 'side_ids'), ('drink', 'drink_ids')]:
        ids = meta.get(key, [])
        if not isinstance(ids, list) or len(ids) > 30 or any(type(i) is not int or i < 1 for i in ids) or len(ids) != len(set(ids)):
            raise HTTPException(400, 'Seleção de acompanhamentos ou bebidas inválida.')
        if kind == 'drink' and not clean['is_combo']:
            ids = []
        options = []
        for item_id in ids:
            row = conn.execute('SELECT name FROM included_choices195 WHERE id=? AND professional_id=? AND kind=? AND available=1', (item_id, professional_id, kind)).fetchone()
            if not row:
                raise HTTPException(400, 'Um acompanhamento ou bebida está indisponível ou não pertence à sua loja.')
            options.append(row['name'])
        clean[key] = ids
        if kind == 'side':
            count = integer(meta.get('side_count', 1), 1, 30, 'Acompanhamentos')
            clean['side_count'] = count
            if options:
                if count > len(options):
                    raise HTTPException(400, 'A quantidade de acompanhamentos supera as opções selecionadas.')
                groups.append({'id': 'side195', 'name': 'Escolha seus acompanhamentos', 'min': count if clean['side_required'] else 0, 'max': count, 'options': options})
        elif clean['is_combo']:
            if not options:
                raise HTTPException(400, 'Selecione pelo menos uma bebida para este combo.')
            groups.append({'id': 'drink195', 'name': 'Escolha sua bebida', 'min': 1, 'max': 1, 'options': options})
    output = parse_config({**config, 'groups': groups})
    output['included195'] = clean
    return output


def register(app, db, require_user, require_premium_catalog):
    @app.post('/painel/cardapio/incluidos195')
    def save_included(request: Request,
                      kind: str = Form(...), name: str = Form(...), item_id: int = Form(0), available: str = Form('')):
        user = require_user(request, 'professional')
        conn = db()
        try:
            pro = require_premium_catalog(conn, user['id'])
            if kind not in ('side', 'drink') or not name.strip() or len(name.strip()) > 100:
                raise HTTPException(400, 'Informe um nome com até 100 caracteres.')
            if item_id:
                row = conn.execute('SELECT * FROM included_choices195 WHERE id=? AND professional_id=? AND kind=?', (item_id, pro['id'], kind)).fetchone()
                if not row:
                    raise HTTPException(404, 'Item não encontrado.')
                if not available:
                    for product in conn.execute("SELECT customization192 FROM products WHERE professional_id=? AND customization192!=''", (pro['id'],)):
                        meta = parse_config(product['customization192']).get('included195', {})
                        if item_id in meta.get('side_ids', []) + meta.get('drink_ids', []):
                            raise HTTPException(400, 'Remova este item dos produtos vinculados antes de marcá-lo indisponível.')
                conn.execute('UPDATE included_choices195 SET name=?,available=? WHERE id=? AND professional_id=?', (name.strip(), int(bool(available)), item_id, pro['id']))
                for product in conn.execute("SELECT id,customization192 FROM products WHERE professional_id=? AND customization192!=''", (pro['id'],)).fetchall():
                    config = parse_config(product['customization192'])
                    if config.get('included195'):
                        save_config(conn, product['id'], resolve(conn, pro['id'], config))
            else:
                conn.execute('INSERT INTO included_choices195(professional_id,kind,name,available) VALUES(?,?,?,?)', (pro['id'], kind, name.strip(), int(bool(available))))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            raise HTTPException(400, 'Este nome já está cadastrado nesta lista.')
        finally:
            conn.close()
        return RedirectResponse('/painel?ok=incluido#cardapio', 303)

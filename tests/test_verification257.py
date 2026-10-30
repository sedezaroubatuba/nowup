import io
import sqlite3
from types import SimpleNamespace
import pytest
from PIL import Image
from fastapi import HTTPException
import nowup_verification257 as v
from test_checkout247 import checkout

def test_digits():
    assert v.valid_doc('11.222.333/0001-81',14)
    assert not v.valid_doc('11.222.333/0001-80',14)
    assert v.valid_doc('529.982.247-25',11)
    assert not v.valid_doc('11111111111',11)

def test_evidence_and_private_storage(tmp_path,monkeypatch):
    def db():
        c=sqlite3.connect(tmp_path/'test.db');c.row_factory=sqlite3.Row;return c
    monkeypatch.setitem(v.G,'db',db)
    with db() as c:c.execute('CREATE TABLE professionals(id INTEGER PRIMARY KEY)');c.execute('INSERT INTO professionals VALUES(1)')
    v.initialize()
    out=io.BytesIO();Image.new('RGB',(30,30)).save(out,'PNG')
    fields=dict(legal_name='Loja',owner_name='Responsável',owner_cpf='52998224725',owner_role='Titular')
    uploads={k:SimpleNamespace(filename='foto.png',file=io.BytesIO(out.getvalue())) for k in v.DOCS}
    docs=v.evidence(fields,uploads,'11222333000181')
    with db() as c:
        v.save(c,1,fields,docs)
        assert c.execute('SELECT COUNT(*) FROM merchant_documents257').fetchone()[0]==4
        with pytest.raises(HTTPException):v.require_review(c,1)
        c.execute("UPDATE merchant_evidence257 SET status='verified'")
        v.require_review(c,1)
    with pytest.raises(HTTPException):v.evidence(fields,{},'11222333000181')

def test_private_routes_reject_customer(checkout):
    m,client,*_=checkout
    assert client.get('/admin/verificacao-lojistas').status_code in (401,403)
    assert client.get('/admin/verificacao-lojistas/1/documentos/identity').status_code in (401,403)
    assert client.get('/painel/documentos').status_code==403

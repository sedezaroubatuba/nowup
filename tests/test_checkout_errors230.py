from __future__ import annotations
import logging
import sqlite3
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from nowup_checkout_errors230 import checkout_errors


def test_expected_error_is_preserved():
    error = HTTPException(409, 'Produto indisponível', headers={'X-Test': 'ok'})
    @checkout_errors
    def endpoint():
        raise error
    with pytest.raises(HTTPException) as caught:
        endpoint()
    assert caught.value is error


def test_failure_is_503_and_logs_traceback(caplog):
    @checkout_errors
    def endpoint():
        raise RuntimeError('simulated failure')
    with caplog.at_level(logging.ERROR), pytest.raises(HTTPException) as caught:
        endpoint()
    assert caught.value.status_code == 503
    assert 'salvo' not in caught.value.detail
    assert 'simulated failure' not in caught.value.detail
    assert caplog.records[-1].exc_info


def test_fastapi_signature_and_success():
    app = FastAPI()
    @app.post('/checkout/{slug}')
    @checkout_errors
    def endpoint(request: Request, slug: str):
        return {'slug': slug, 'method': request.method}
    response = TestClient(app).post('/checkout/store')
    assert response.status_code == 200
    assert response.json() == {'slug': 'store', 'method': 'POST'}


def test_transaction_cleanup_prevents_partial_order(tmp_path):
    path = tmp_path / 'orders.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE orders(id INTEGER PRIMARY KEY)')
    @checkout_errors
    def endpoint():
        conn = sqlite3.connect(path)
        try:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('INSERT INTO orders VALUES(1)')
            raise RuntimeError('before commit')
        finally:
            conn.close()
    with pytest.raises(HTTPException):
        endpoint()
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 0

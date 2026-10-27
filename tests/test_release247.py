"""Regression checks for media lifecycle, auth limits and public references."""
import base64,io,sqlite3
from pathlib import Path
import pytest
from PIL import Image
from fastapi import HTTPException,FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from starlette.requests import Request
from nowup_media247 import MediaConnection,initialize,references
from nowup_media245 import install,TABLE
from nowup_auth247 import check

@pytest.fixture
def media(tmp_path):
    uploads=tmp_path/'uploads';uploads.mkdir()
    def raw():
        c=sqlite3.connect(tmp_path/'db');c.row_factory=sqlite3.Row;return c
    c=raw();initialize(c);c.executescript("CREATE TABLE products(id INTEGER PRIMARY KEY,image_filename TEXT);CREATE TABLE photos(id INTEGER PRIMARY KEY,filename TEXT);CREATE TABLE order_receipts206(filename TEXT);CREATE TABLE site_settings(key TEXT,value TEXT);");c.commit();c.close()
    def db():return MediaConnection(raw(),uploads)
    app=FastAPI();app.mount('/uploads',StaticFiles(directory=uploads));install(app,lambda r,role:None,db,uploads)
    return db,uploads,app

def photo(path):Image.new('RGB',(2,2),'purple').save(path,'JPEG')

def test_image_survives_disk_loss_but_deleted_reference_returns_404(media):
    db,uploads,app=media;photo(uploads/'one.jpg')
    with db() as c:c.execute('INSERT INTO products VALUES(1,?)',('one.jpg',))
    (uploads/'one.jpg').unlink()
    with TestClient(app) as client:
        assert client.get('/uploads/one.jpg').status_code==200
        with db() as c:c.execute('DELETE FROM products WHERE id=1')
        assert client.get('/uploads/one.jpg').status_code==404

def test_shared_image_kept_until_last_reference_and_old_disk_cache_is_denied(media):
    db,uploads,app=media;photo(uploads/'shared.jpg')
    with db() as c:
        c.execute('INSERT INTO products VALUES(1,?)',('shared.jpg',));c.execute('INSERT INTO photos VALUES(1,?)',('shared.jpg',))
    with db() as c:c.execute('DELETE FROM products')
    with TestClient(app) as client:
        assert client.get('/uploads/shared.jpg').status_code==200
        with db() as c:c.execute('DELETE FROM photos')
        assert (uploads/'shared.jpg').exists()
        assert client.get('/uploads/shared.jpg').status_code==404

def test_invalid_image_rolls_back_business_change(media):
    db,uploads,_=media;(uploads/'bad.jpg').write_bytes(b'not an image')
    with pytest.raises(Exception):
        with db() as c:c.execute('INSERT INTO products VALUES(1,?)',('bad.jpg',))
    with db() as c:assert c.execute('SELECT COUNT(*) FROM products').fetchone()[0]==0

def test_private_receipt_and_static_assets_are_not_public_upload_references(media):
    db,_,_=media
    with db() as c:
        c.execute('INSERT INTO order_receipts206 VALUES(?)',('secret.jpg',))
        c.execute('INSERT INTO site_settings VALUES(?,?)',('config','{"photo":"/static/logo.png"}'))
        assert references(c)==set()

def test_auth_limits_shared_between_connections_and_expire(media):
    db,_,_=media;request=Request({'type':'http','method':'POST','path':'/entrar','headers':[],'client':('127.0.0.1',1000)})
    for _ in range(10):check(db,request,'same@example.invalid',now=1200)
    with pytest.raises(HTTPException) as e:check(db,request,'same@example.invalid',now=1201)
    assert e.value.status_code==429
    check(db,request,'other@example.invalid',now=1201)
    check(db,request,'same@example.invalid',now=1800)

"""Separate installation identity must never bypass administrative authentication."""
import json
import sqlite3
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.templating import Jinja2Templates
import nowup_admin227 as admin

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('role', [None,'customer','professional'])
def test_admin_install_entry_does_not_grant_panel_access(monkeypatch,role):
 monkeypatch.setattr(admin,'G',{'db':lambda:sqlite3.connect(':memory:'), 'current_user':lambda request: {'role':role} if role else None, 'templates':Jinja2Templates(directory=str(ROOT/'templates'))})
 app=FastAPI();app.include_router(admin.router)
 with TestClient(app,follow_redirects=False) as client:
  login=client.get('/admin/super/entrar')
  assert login.status_code==200
  assert 'name="tipo" value="admin"' in login.text
  assert '/static/nowup-admin.webmanifest' in login.text
  assert client.get('/admin/super').headers['location']=='/admin/super/entrar'
  assert client.get('/admin/super/api/state').status_code==401

def test_distinct_install_identity_covers_login_and_verification():
 adm=json.loads((ROOT/'static/nowup-admin.webmanifest').read_text())
 public=json.loads((ROOT/'static/nowup.webmanifest').read_text())
 assert adm['id']!=public['id']
 assert adm['name']=='NowUp Super ADM'
 assert adm['start_url'].startswith(adm['scope'])
 assert '/admin/codigo'.startswith(adm['scope'])
 for name in ['templates/admin_login.html','templates/admin_code.html','static/adm227/index.html','frontend-admin/index.html']:
  assert '/static/nowup-admin.webmanifest' in (ROOT/name).read_text()

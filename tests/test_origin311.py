"""Auth pages retain provenance for Chrome form submissions."""
from pathlib import Path
import pytest
from starlette.requests import Request
from nowup_runtime238 import mutation_origin_allowed

@pytest.mark.parametrize("path", ["/entrar", "/admin/codigo", "/redefinir-senha", "/recuperar-senha", "/admin/super/equipe/entrar"])
def test_auth_form_same_origin_and_cross_site(path, monkeypatch):
    monkeypatch.delenv("NOWUP_PUBLIC_ORIGIN", raising=False)
    monkeypatch.delenv("NOWUP_HTTPS", raising=False)
    def check(origin, site):
        return mutation_origin_allowed(Request(dict(type="http", method="POST", scheme="https", path=path, root_path="", query_string=b"", server=("testserver",443), headers=[(b"host",b"testserver"),(b"origin",origin.encode()),(b"sec-fetch-site",site.encode())])))
    assert check("https://testserver", "same-origin")
    assert not check("null", "same-origin")
    assert not check("https://evil.invalid", "cross-site")

def test_auth_referrer_policy_preserves_same_origin():
    root=Path(__file__).resolve().parents[1]
    app=(root/"app.py").read_text()
    team=(root/"nowup_admin227.py").read_text()
    assert 'response.headers["Referrer-Policy"]="same-origin"' in app
    assert "'Referrer-Policy':'same-origin'" in team
    assert "no-referrer" not in team

import pytest
from test_checkout247 import checkout

@pytest.mark.parametrize('path', ['/contato', '/noticias', '/pagina/auditoria-340', '/noticias/auditoria-340'])
def test_public_cms_renders_shared_readable_theme(checkout, monkeypatch, path):
    import cms
    m, client, *_ = checkout
    monkeypatch.setattr(cms, 'DB_PATH', m.DB_PATH)
    cms.init_cms_db()
    with m.db() as c:
        c.execute("INSERT INTO cms_pages(title,slug,content,status,created_at,updated_at) VALUES('Auditoria','auditoria-340','Conteúdo','published',?,?)", (cms.now_iso(), cms.now_iso()))
        c.execute("INSERT INTO cms_posts(title,slug,content,status,created_at,updated_at) VALUES('Auditoria','auditoria-340','Conteúdo','published',?,?)", (cms.now_iso(), cms.now_iso()))
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert '/static/surfaces340.css?v=341' in response.text

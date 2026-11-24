"""V461: regression against malformed <script> tags that stopped bulk search."""
from bs4 import BeautifulSoup
from test_merchant228 import env

def test_bulk_scripts_are_separate_valid_tags_and_search_catalog_is_present(env):
    m, client, _, store, _ = env
    result=client.get("/painel/todos-produtos")
    assert result.status_code==200
    soup=BeautifulSoup(result.text,"html.parser")
    scripts=soup.find_all("script")
    by_src={tag.get("src"):tag for tag in scripts if tag.get("src")}
    assert "/static/all-products455.js?v=461" in by_src
    assert "/static/product-bulk460.js?v=465" in by_src
    for path in ("/static/all-products455.js?v=461","/static/product-bulk460.js?v=465"):
        assert not by_src[path].text.strip()
    catalog=soup.select_one("#nu455-product-names")
    assert catalog is not None
    import json
    assert isinstance(json.loads(catalog.text), list)
    assert soup.select_one('[data-bulk-search460]')
    assert soup.select_one('[data-bulk-results460]')

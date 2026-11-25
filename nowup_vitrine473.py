"""Vitrine shelves backed by the public store catalog."""
from itertools import zip_longest

from nowup_groups260 import effective_promo_cents
from nowup_search177 import normalize


def is_vitrine_product(row):
    return "tabacaria" not in normalize(row.get("category"))


def browse_item(row, status):
    item = dict(row)
    promo = effective_promo_cents(item)
    item.update(promo=promo, price=promo or item["price_cents"], open=bool(status["open"]))
    item["requires_options"] = any(item.get(key) for key in (
        "is_dish", "is_combo256", "sold_by_weight370", "is_group_header260", "group_parent_id260",
    )) or item.get("business_type") == "fashion"
    return item


def shelves(conn, store):
    rows = conn.execute("""
        SELECT pr.* FROM products pr
        WHERE pr.professional_id=? AND pr.available=1 AND pr.group_parent_id260=0
        AND (lower(pr.category)='combos' OR NOT EXISTS (
            SELECT 1 FROM product_categories pc
            WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category)
        ) OR EXISTS (
            SELECT 1 FROM product_categories pc
            WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category) AND pc.active=1
        ))
        ORDER BY pr.featured DESC, pr.sort_order, pr.id DESC
    """, (store["id"],)).fetchall()
    products = [browse_item(row, store["shop_status"]) for row in rows if not row["is_group_header260"] and is_vitrine_product(dict(row))]
    covers = {
        "cervejas": ("Cervejas", ("cerveja", "chopp")),
        "refrigerantes": ("Refrigerantes", ("refrigerante", "bebidas nao alcoolicas", "bebidas nao alcolicas")),
        "promocoes": ("Promoções", ()),
        "mercearia": ("Mercearia", ("mercearia",)),
    }
    groups = {}
    for key, (title, terms) in covers.items():
        items = [p for p in products if (p["promo"] > 0 if key == "promocoes" else
                 any(term in normalize(p["category"]) for term in terms))]
        if key == "refrigerantes":
            items = [p for p in items if not any(word in normalize(p["name"]).split() for word in ("agua","suco","energetico","isotonico"))]
        groups[key] = (title, items)
    chocolates = [p for p in products if "chocolate" in normalize(p["category"])]
    recommendations = []
    seen = set()
    for group in zip_longest(*(items[:12] for _, items in groups.values())):
        for item in group:
            if item is None or item["id"] in seen:
                continue
            recommendations.append(item)
            seen.add(item["id"])
    return groups, chocolates, recommendations[:12]

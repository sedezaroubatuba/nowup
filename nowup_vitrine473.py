"""Vitrine shelves backed by the public store catalog."""
from itertools import zip_longest
from collections import defaultdict
from random import SystemRandom
import re

from nowup_groups260 import effective_promo_cents
from nowup_search177 import normalize
from nowup_custom192 import parse_config
from nowup_combos303 import current_price


def is_vitrine_product(row):
    return "tabacaria" not in normalize(row.get("category"))


def browse_item(row, status):
    item = dict(row)
    promo = effective_promo_cents(item)
    item.update(promo=promo, price=promo or item["price_cents"], open=bool(status["open"]))
    item["discount_pct"] = int((100*(item["price_cents"]-promo)/item["price_cents"])+0.5) if promo and item["price_cents"]>promo else 0
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
    # Compare exactly the same catalogue components and current separate prices as the store.
    combo_prices = {str(row["id"]): current_price(row) for row in conn.execute(
        "SELECT id,price_cents,promo_price_cents FROM products WHERE professional_id=? AND available=1 AND is_combo256=0",
        (store["id"],)).fetchall()}
    for p in products:
        if p.get("is_combo256") and p.get("customization192"):
            try:
                comparison=combo_comparison512(parse_config(p["customization192"]),combo_prices,p["price"])
                if comparison:
                    p.update(comparison)
            except Exception:
                # An incomplete comparison never creates an invented savings badge.
                pass
    covers = {
        "cervejas": ("Cervejas", ("cerveja", "chopp")),
        "refrigerantes": ("Refrigerantes", ("refrigerante", "bebidas nao alcoolicas", "bebidas nao alcolicas")),
        "promocoes": ("Promoções", ()),
        "mercearia": ("Mercearia", ("mercearia",)),
        "energeticos": ("Energéticos", ("energetico",)),
        "destilados": ("Destilados", ("destilado", "bebidas quentes", "bebidas alcoolicas gerais", "whisky", "vodka")),
        "lanches": ("Lanches", ("lanche", "refeicao")),
        "combos": ("Combos", ("combo",)),
    }
    groups = {}
    for key, (title, terms) in covers.items():
        items = [p for p in products if (p["promo"] > 0 if key == "promocoes" else
                 any(term in normalize(p["category"]) for term in terms))]
        if key == "energeticos":
            items = [p for p in products if "energetico" in normalize(p["category"]) or any(word in normalize(p["name"]) for word in ("energetico", "monster", "red bull", "redbull"))]
        if key == "combos":
            items = [p for p in products if p.get("is_combo256") or "combo" in normalize(p["category"])]
        if key == "refrigerantes":
            items = [p for p in items if not any(word in normalize(p["name"]).split() for word in ("agua","suco","energetico","isotonico"))]
        groups[key] = (title, items)
    groups["geladas"] = ("Bebidas geladas", [p for p in products if p.get("sold_cold")])
    chocolates = [p for p in products if "chocolate" in normalize(p["category"])]
    # Dynamically expose new catalogue categories without duplicating standard shelves.
    standard = {p["id"] for key, (_, items) in groups.items() if key not in ("promocoes", "geladas") for p in items}
    for p in products:
        label = (p.get("category") or "").strip()
        normalized = normalize(label)
        if not label or any(term in normalized for term in ("chocolate", "cigarro", "tabaco", "tabacaria", "narguile")) or p["id"] in standard:
            continue
        key = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
        if not key:
            continue
        key = "extra-" + key
        if key not in groups:
            groups[key] = (label, [])
        groups[key][1].append(p)
    recommendations = []
    seen = set()
    for group in zip_longest(*(items[:12] for _, items in groups.values())):
        for item in group:
            if item is None or item["id"] in seen:
                continue
            recommendations.append(item)
            seen.add(item["id"])
    return groups, chocolates, recommendations[:12]


def marketplace_shelves(conn, stores):
    """Round-robin, with randomized store order and bounded per-store shelf lists."""
    rng = SystemRandom()
    pools = defaultdict(list)
    titles = {}
    chocolate_pools = []
    recommendation_pools = []
    for store in stores:
        groups, chocolates, recommendations = shelves(conn, store)
        def annotated(items):
            return [dict(p, store_slug=store["slug"], store_name=store["display_name"],
                         store_user_id=store["user_id"]) for p in items]
        for key, (title, items) in groups.items():
            titles[key] = title
            if items:
                pools[key].append(annotated(items))
        if chocolates:
            chocolate_pools.append(annotated(chocolates))
        if recommendations:
            recommendation_pools.append(annotated(recommendations))

    def interleave(queues, limit=96):
        queues = [list(q) for q in queues if q]
        if len(queues) > 1:
            rng.shuffle(queues)
            for queue in queues:
                # Rotate the leading selection without wiping merchandising order.
                featured = queue[:min(12, len(queue))]
                rng.shuffle(featured)
                queue[:len(featured)] = featured
        result = []
        for lane in zip_longest(*queues):
            result.extend(p for p in lane if p is not None)
            if len(result) >= limit:
                break
        return result[:limit]

    groups = {key: (title, interleave(pools[key])) for key, title in titles.items()}
    return groups, interleave(chocolate_pools), interleave(recommendation_pools, 12)


def combo_comparison512(config, prices, final):
    items=config.get("combo_items",[])
    if not items or not isinstance(final,int) or final<0:
        return None
    separate=0; variable=False
    for item in items:
        qty=item.get("quantity")
        if not isinstance(qty,int) or not 1<=qty<=99:
            return None
        group=next((g for g in config.get("groups",[]) if g.get("id")==item.get("group_id301")),None)
        if group:
            ids=group.get("product_ids",[])
            if not ids or len(ids)!=len(group.get("options",[])):
                return None
            costs=[prices.get(str(pid)) for pid in ids]
            if any(not isinstance(cost,int) or cost<0 for cost in costs):
                return None
            separate+=min(costs)*qty
            variable=variable or min(costs)!=max(costs)
        else:
            cost=prices.get(str(item.get("product_id")))
            if not isinstance(cost,int) or cost<0:
                return None
            separate+=cost*qty
    return {"combo_separate":separate,"combo_saving":max(0,separate-final),"combo_variable":variable}

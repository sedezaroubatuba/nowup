"""V460: atomic, store-scoped bulk editing, at most ten products per operation."""
from __future__ import annotations

import json
from urllib.parse import urlencode

from fastapi import Request, Form, HTTPException
from fastapi.responses import RedirectResponse

import nowup_subcategories448


MAX_BULK460 = 10


def _unique_ids460(ids):
    if not 1 <= len(ids) <= MAX_BULK460:
        raise HTTPException(400, "Selecione de 1 a 10 produtos por operação.")
    if any(not isinstance(pid, int) or pid <= 0 for pid in ids) or len(set(ids)) != len(ids):
        raise HTTPException(400, "A seleção contém produtos inválidos ou duplicados.")
    return ids


def _price_map460(raw, ids, converter):
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        raise HTTPException(400, "Confira os novos preços antes de salvar.")
    if not isinstance(data, dict) or set(data) != {str(i) for i in ids}:
        raise HTTPException(400, "Informe um preço novo para cada produto selecionado.")
    prices = {}
    for pid in ids:
        value = data[str(pid)]
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(400, "Todos os produtos selecionados precisam de um preço.")
        cents = converter(value.strip())
        if cents <= 0:
            raise HTTPException(400, "O preço deve ser maior que zero.")
        prices[pid] = cents
    return prices


def install(ns):
    app, db = ns["app"], ns["db"]
    require_user = ns["require_user"]
    require_premium_catalog = ns["require_premium_catalog"]
    price_to_cents = ns["price_to_cents"]
    now_iso = ns["now_iso"]

    @app.post("/painel/todos-produtos/lote")
    def bulk_update460(request: Request, selected_ids: list[int] = Form([]),
                       operation: str = Form(...), target_id: int = Form(0),
                       new_category: str = Form(""), subcategory_id261: int = Form(0),
                       prices_json: str = Form(""), available_value: str = Form("")):
        # Selection is explicitly submitted, not derived from a broad search/filter.
        ids = _unique_ids460(selected_ids)
        if operation not in {"related", "category", "prices", "availability"}:
            raise HTTPException(400, "Escolha uma alteração em lote válida.")
        from nowup_sales107 import check_origin
        check_origin(request)
        user = require_user(request, "professional")
        conn = db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            pro = require_premium_catalog(conn, user["id"])
            suffix = " FOR UPDATE" if getattr(conn, "dialect", "sqlite") == "postgres" else ""
            placeholders = ",".join("?" for _ in ids)
            rows = conn.execute(
                f"SELECT * FROM products WHERE professional_id=? AND id IN ({placeholders})" + suffix,
                (pro["id"], *ids)).fetchall()
            if len(rows) != len(ids):
                raise HTTPException(404, "Um dos produtos não pertence à loja ou não existe.")
            by_id = {int(r["id"]): dict(r) for r in rows}
            updates = {}
            if operation == "related":
                target = conn.execute("SELECT * FROM products WHERE id=? AND professional_id=?",
                                      (target_id, pro["id"])).fetchone()
                if not target or target["is_group_header260"]:
                    raise HTTPException(400, "Escolha um produto real da sua loja para o Leve Junto.")
                for pid in ids:
                    product = by_id[pid]
                    if product["is_group_header260"]:
                        raise HTTPException(400, "Capa de agrupador não pode receber Leve Junto; escolha itens reais.")
                    if pid == target_id:
                        raise HTTPException(400, "O mesmo produto não pode sugerir a si próprio.")
                    old = [int(x) for x in str(product["related256"] or "").split(",") if x.isdigit()]
                    values = list(dict.fromkeys(old + [target_id]))
                    if len(values) > 20:
                        raise HTTPException(400, f"O produto {product['name']} já atingiu 20 sugestões.")
                    updates[pid] = {"related256": ",".join(map(str, values))}
            elif operation == "category":
                cat = conn.execute(
                    "SELECT name FROM product_categories WHERE professional_id=? AND active=1 AND lower(name)=lower(?)",
                    (pro["id"], new_category.strip())).fetchone()
                if not cat:
                    raise HTTPException(400, "Escolha uma categoria ativa da sua loja.")
                subcat = nowup_subcategories448.valid_selection(
                    conn, pro["id"], cat["name"], subcategory_id261)
                for pid in ids:
                    product = by_id[pid]
                    if product["is_group_header260"] or product["group_parent_id260"]:
                        raise HTTPException(
                            400, "Produtos vinculados a agrupadores devem mudar de categoria pelo editor do agrupador, para preservar todos os vínculos.")
                    updates[pid] = {"category": cat["name"], "subcategory_id261": subcat}
            elif operation == "prices":
                prices = _price_map460(prices_json, ids, price_to_cents)
                for pid in ids:
                    product = by_id[pid]
                    if product["is_group_header260"]:
                        raise HTTPException(400, "A capa de agrupador não tem preço próprio. Selecione seus produtos individuais.")
                    if 0 < int(product["promo_price_cents"] or 0) >= prices[pid]:
                        raise HTTPException(400, f"O novo preço de {product['name']} precisa ser maior que seu preço promocional.")
                    updates[pid] = {"price_cents": prices[pid]}
            else:
                if available_value not in {"0", "1"}:
                    raise HTTPException(400, "Escolha Disponível ou Indisponível.")
                active = int(available_value)
                for pid in ids:
                    product = by_id[pid]
                    if active and not product["is_group_header260"] and int(product["price_cents"]) <= 0:
                        raise HTTPException(400, f"{product['name']} está sem preço e não pode ser ativado.")
                    updates[pid] = {"available": active}

            # All conditions are validated before the first update. One SQL
            # transaction covers updates and audit, so errors roll everything back.
            changed = 0
            stamp = now_iso()
            for pid in ids:
                original = by_id[pid]
                delta = {key: {"antes": original[key], "depois": value}
                         for key, value in updates[pid].items() if original[key] != value}
                if not delta:
                    continue
                changes = {key: value["depois"] for key, value in delta.items()}
                sets = ",".join(f"{key}=?" for key in changes)
                conn.execute(f"UPDATE products SET {sets},updated_at=? WHERE id=? AND professional_id=?",
                             (*changes.values(), stamp, pid, pro["id"]))
                conn.execute(
                    "INSERT INTO product_audit455(professional_id,product_id,actor_id,detail,created_at) VALUES(?,?,?,?,?)",
                    (pro["id"], pid, user["id"], json.dumps(delta, ensure_ascii=False), stamp))
                changed += 1
            conn.commit()
            return RedirectResponse(
                "/painel/todos-produtos?" +
                urlencode({"ok": "lote", "changed": changed, "selected": len(ids)}) +
                "#lote460", 303)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

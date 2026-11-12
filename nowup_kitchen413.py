"""Shared catalogue choices and immutable kitchen details for merchant checkout."""
import json
from fastapi import HTTPException
from nowup_custom192 import parse_config,validate_customization
from nowup_combo_units364 import children,validate_units
from nowup_combo_pack305 import build_pack,read_pack
from nowup_combos303 import current_price


def metadata(c,pid,product):
    cfg=parse_config(product['customization192'])
    result=children(c,pid,{str(product['id'])}).get(str(product['id']))
    if not result:
        result={'id':product['id'],'name':product['name'],'config':cfg,'options':[],'limits':[],'max':0}
    result['config']=cfg
    result['combo']=bool(product['is_combo256'] or cfg.get('meal_combo324'))
    if result['combo']:
        ids={str(i['product_id']) for i in cfg.get('combo_items',[]) if i.get('product_id')}
        for group in cfg['groups']:
            ids.update(str(i) for i in group.get('product_ids',[]))
            ids.update(str(r['id']) for r in group.get('item_refs325',[]) if r['kind']=='product')
        result['children']=children(c,pid,ids)
    else:result['children']={}
    return result


def needs_choices(c,pid,product):
    cfg=parse_config(product['customization192'])
    return bool(product['is_combo256'] or cfg.get('is_meal317') or cfg.get('meal_combo324') or cfg['ingredients'] or cfg['groups'] or cfg.get('question333') or (product['extras_mode']!='none' and c.execute('SELECT 1 FROM product_options WHERE product_id=? AND available=1 LIMIT 1',(product['id'],)).fetchone()))


def compose(g,c,pid,product,raw):
    if not isinstance(raw,dict):raise HTTPException(400,'Escolhas inválidas.')
    if not isinstance(raw.get('notes',''),str) or len(raw.get('notes',''))>300:raise HTTPException(400,'Observação inválida.')
    cfg=parse_config(product['customization192']);selected=raw.get('customization',{})
    chosen,extras=g['options_single158'](c,product['id'],raw.get('options',[]));g['validate_choices89'](c,product['id'],chosen)
    description=validate_customization(cfg,selected,raw.get('notes',''),raw.get('utensils',False))
    lines=[]
    if cfg['ingredients']:lines.append('Composição: '+', '.join(i['name'] for i in cfg['ingredients'] if i['name'] not in selected.get('removed',[])))
    if description:lines.append(description)
    units=[];extra_units=0;pack=''
    if product['is_combo256'] or cfg.get('meal_combo324'):
        units,child_options,extra_units=validate_units(g,c,pid,cfg,selected)
        pack=build_pack(cfg,selected,raw.get('notes',''),units,description)
        snapshot=read_pack(pack)
        if snapshot:
            lines.append('Itens do combo:')
            lines.extend(str(i['quantity'])+' × '+i['name'] for i in snapshot['items'])
        registry=metadata(c,pid,product)['children']
        for unit in units:
            child=registry[str(unit['product_id'])];child_raw=next((r for r in selected.get('units364',[]) if r.get('key')==unit['key']),{})
            recipe=', '.join(i['name'] for i in child['config']['ingredients'] if i['name'] not in child_raw.get('customization',{}).get('removed',[]))
            lines.append(unit['name']+' '+str(unit['position'])+': '+(unit['notes'] or 'Completo'))
            if recipe:lines.append('Composição: '+recipe)
            lines.extend('+ '+o['name']+' — R$ '+format(o['price_cents']/100,'.2f').replace('.',',') for o in unit['options'])
    elif selected.get('units364'):raise HTTPException(400,'Este produto não possui unidades de combo.')
    lines.extend('+ '+o['name']+' — R$ '+format(o['price_cents']/100,'.2f').replace('.',',') for o in chosen)
    if cfg.get('combo_notice316'):lines.append('Aviso do combo: '+cfg['combo_notice316'])
    return current_price(product)+extras+extra_units,'\n'.join(lines),json.dumps({'config':cfg,'choices':raw,'combo_pack':pack},ensure_ascii=False)

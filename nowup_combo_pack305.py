"""Immutable, per-combo picking lists created after checkout validation."""
import json
from collections import Counter


def build_pack(config, selected, note='', units=None):
    rows=[];done=set();choices=selected.get('groups',{})
    def add(name,quantity,role,group='',product_id=None):
        if quantity:rows.append({'name':name,'quantity':quantity,'role':role,'group':group,'product_id':product_id})
    groups={g['id']:g for g in config.get('groups',[])}
    for item in config.get('combo_items',[]):
        group=groups.get(item.get('group_id301'))
        if group:
            for name,quantity in Counter(choices.get(group['id'],[])).items():
                index=group['options'].index(name)
                refs=group.get('product_ids',[])
                add(name,quantity,'included',group['name'],refs[index] if index<len(refs) else None)
            done.add(group['id'])
        else:add(item['name'],item['quantity'],'principal' if item.get('principal') else 'included','',item.get('product_id'))
    for group in config.get('groups',[]):
        if group['id'] not in done:
            for name,quantity in Counter(choices.get(group['id'],[])).items():add(name,quantity,'included',group['name'])
    for item in config.get('combo_manual',[]):add(item['name'],item['quantity'],'manual','Itens manuais')
    return json.dumps({'version':1,'items':rows,'units364':units or [],'note':str(note)[:300],'notice316':str(config.get('combo_notice316',''))[:600]},ensure_ascii=False,separators=(',',':')) if rows else ''


def read_pack(value):
    try:
        data=json.loads(value) if isinstance(value,str) else value
        if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('items'),list) or not 1<=len(data['items'])<=400:return None
        for row in data['items']:
            if not isinstance(row,dict) or not isinstance(row.get('name'),str) or len(row['name'])>140 or type(row.get('quantity')) is not int or not 1<=row['quantity']<=99 or row.get('role') not in ('principal','included','manual'):return None
        units=data.get('units364',[])
        if not isinstance(units,list) or len(units)>400:return None
        for unit in units:
            if not isinstance(unit,dict) or not isinstance(unit.get('name'),str) or type(unit.get('position')) is not int or not 1<=unit['position']<=400 or not isinstance(unit.get('notes',''),str) or not isinstance(unit.get('options',[]),list):return None
            for extra in unit.get('options',[]):
                if not isinstance(extra,dict) or not isinstance(extra.get('name'),str) or type(extra.get('price_cents')) is not int or extra['price_cents']<0:return None
        if not isinstance(data.get('note',''),str):return None
        if not isinstance(data.get('notice316',''),str) or len(data.get('notice316',''))>600:return None
        return data
    except (ValueError,TypeError):return None

"""Per-unit customization of existing store products included in a combo."""
from collections import Counter
from fastapi import HTTPException
from nowup_custom192 import parse_config, validate_customization
from nowup_ingredients320 import catalog, attach_photos329


def children(conn, store_id, ids, photos=None):
    result={}
    if not ids:return result
    photos=catalog(conn,store_id) if photos is None else photos
    for source in conn.execute('SELECT * FROM products WHERE professional_id=? AND available=1 AND is_combo256=0',(store_id,)):
        row=dict(source)
        if str(row['id']) not in ids:continue
        config=attach_photos329(parse_config(row.get('customization192','')),photos)
        editable=bool(config['ingredients'] or config['groups'] or config.get('question333') or config.get('is_meal317'))
        options=[];limits=[]
        if row.get('extras_mode','none')!='none':
            options=[dict(o) for o in conn.execute('SELECT id,name,price_cents,group_id FROM product_options WHERE product_id=? AND available=1 ORDER BY sort_order,id',(row['id'],))]
            limits=[dict(g) for g in conn.execute('SELECT id,name,min_choices,max_choices FROM product_option_groups WHERE product_id=?',(row['id'],)) if row['extras_mode'] not in ('all','selected') or g['name']=='Adicionais']
        result[str(row['id'])]={'id':row['id'],'name':row.get('name','Produto'),'config':config,'options':options,'limits':limits,'max':max([g['max_choices'] for g in limits] or [3]),'editable':editable or bool(options)}
    return result


def slots(config, selected):
    rows=[];done=set();groups={g['id']:g for g in config.get('groups',[])}
    def group_rows(group,prefix):
        values=selected.get('groups',{}).get(group['id'],[])
        refs=group.get('product_ids',[])
        for index,name in enumerate(values):
            option=group['options'].index(name)
            if option<len(refs):rows.append((prefix+'u'+str(index),refs[option]))
    for index,item in enumerate(config.get('combo_items',[])):
        group=groups.get(item.get('group_id301'))
        if group:group_rows(group,'i'+str(index));done.add(group['id'])
        elif item.get('product_id'):
            rows.extend(('i'+str(index)+'u'+str(unit),item['product_id']) for unit in range(item['quantity']))
    for index,group in enumerate(config.get('groups',[])):
        if group['id'] not in done:group_rows(group,'g'+str(index))
    if len(rows)>400:raise HTTPException(400,'Este combo tem unidades demais. Divida os itens.')
    return rows


def validate_units(g,conn,store_id,config,selected):
    positions=slots(config,selected)
    if not positions:
        if selected.get('units364'):raise HTTPException(400,'As unidades do combo mudaram. Atualize o combo.')
        return [],[],0
    registry=children(conn,store_id,{str(pid) for _,pid in positions})
    if any(str(pid) not in registry for _,pid in positions):raise HTTPException(400,'Um produto deste combo ficou indisponível. Atualize o cardápio.')
    for pid in {pid for _,pid in positions}:
        if conn.execute("SELECT 1 FROM products pr WHERE pr.id=? AND EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category)) AND NOT EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category) AND pc.active=1)",(pid,)).fetchone():raise HTTPException(400,'Um produto deste combo ficou indisponível. Atualize o cardápio.')
    raw=selected.get('units364',[])
    if not isinstance(raw,list) or len(raw)>400 or any(not isinstance(v,dict) for v in raw):raise HTTPException(400,'Personalização das unidades inválida.')
    indexed={}
    allowed={key:pid for key,pid in positions if registry[str(pid)]['editable']}
    for unit in raw:
        key=unit.get('key');pid=unit.get('product_id')
        if not isinstance(key,str) or key not in allowed or type(pid) is not int or allowed[key]!=pid or key in indexed:raise HTTPException(400,'As unidades do combo mudaram. Atualize o combo.')
        indexed[key]=unit
    output=[];charged=[];total=0;counts=Counter()
    for key,pid in positions:
        child=registry[str(pid)]
        if not child['editable']:continue
        counts[pid]+=1;label=child['name']+' '+str(counts[pid]);unit=indexed.get(key,{})
        notes=unit.get('notes','')
        if not isinstance(notes,str) or len(notes)>300:raise HTTPException(400,'Observação da unidade inválida.')
        try:
            details=validate_customization(child['config'],unit.get('customization',{}),notes,unit.get('utensils',False))
            options,price=g['options_single158'](conn,pid,unit.get('options',[]))
            g['validate_choices89'](conn,pid,options)
        except HTTPException as error:raise HTTPException(error.status_code,label+': '+str(error.detail)) from error
        total+=price
        clean_options=[{**dict(o),'name':label+': '+o['name']} for o in options]
        charged.extend(clean_options)
        output.append({'key':key,'product_id':pid,'name':child['name'],'position':counts[pid],'notes':details,'options':[{'name':o['name'],'price_cents':o['price_cents']} for o in options]})
    return output,charged,total

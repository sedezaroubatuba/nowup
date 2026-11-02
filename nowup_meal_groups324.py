"""Resolve meal choice groups against the merchant's own catalog before saving."""
from nowup_custom192 import fail, parse_config


def resolve(conn, store_id, config):
    if not config.get('is_meal317'):
        fail('Os grupos de refeição devem pertencer a um lanche ou refeição.')
    enabled=config.get('meal_combo324',False)
    groups=config['groups']
    if enabled and not groups:
        fail('Adicione pelo menos um grupo de escolhas ao combo.')
    if not enabled and groups:
        fail('Ative o combo para cadastrar grupos de escolhas.')
    clean=[]
    for group in groups:
        if not group.get('quantity_mode') or group['min']!=group['max']:
            fail('Defina a quantidade exata de cada grupo do combo.')
        options=[]
        sources=group.get('item_refs325')
        if sources is None:
            refs=group.get('product_ids',[])
            if not refs or len(refs)!=len(group['options']) or len(refs)!=len(set(refs)):
                fail('Importe os produtos da própria loja para cada grupo, sem repetir opções.')
            sources=[{'kind':'product','id':ref} for ref in refs]
        for index,ref in enumerate(sources):
            if ref['kind']=='manual':
                options.append(group['options'][index]);continue
            if ref['kind']=='item':
                row=conn.execute('SELECT name FROM ingredients320 WHERE id=? AND professional_id=?',(ref['id'],store_id)).fetchone()
            else:
                row=conn.execute('SELECT name FROM products WHERE id=? AND professional_id=? AND available=1 AND is_combo256=0',(ref['id'],store_id)).fetchone()
            if not row:fail('Um item do grupo está indisponível ou não pertence à sua loja.')
            options.append(row['name'])
        if len({name.casefold() for name in options})!=len(options):fail('Não repita itens no mesmo grupo.')
        clean.append({**group,'options':options})
    result=parse_config({**config,'groups':clean})
    result['included195']={'side_ids':[],'drink_ids':[],'side_count':1,'side_required':False,'is_combo':False}
    return result

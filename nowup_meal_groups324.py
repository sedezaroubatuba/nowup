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
        refs=group.get('product_ids',[])
        if not refs or len(refs)!=len(group['options']) or len(refs)!=len(set(refs)):
            fail('Importe os produtos da própria loja para cada grupo, sem repetir opções.')
        if not group.get('quantity_mode') or group['min']!=group['max']:
            fail('Defina a quantidade exata de cada grupo do combo.')
        options=[]
        for ref in refs:
            row=conn.execute('SELECT name FROM products WHERE id=? AND professional_id=? AND available=1 AND is_combo256=0',(ref,store_id)).fetchone()
            if not row:fail('Um produto do grupo está indisponível ou não pertence à sua loja.')
            options.append(row['name'])
        clean.append({**group,'options':options})
    result=parse_config({**config,'groups':clean})
    result['included195']={'side_ids':[],'drink_ids':[],'side_count':1,'side_required':False,'is_combo':False}
    return result

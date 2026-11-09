"""Editable illustrative measurement templates; never infer stock from a guide."""
import json
from fastapi import HTTPException

PRESETS={
 'letters':dict(title='Roupas por letras — referência',text='Tamanho;Busto (cm);Cintura (cm);Quadril (cm)\nPP;76–83;62–69;82–89\nP;84–88;70–74;90–94\nM;89–96;75–82;95–102\nG;97–104;83–90;103–110\nGG;105–112;91–98;111–118\nXXG;113–120;99–106;119–126'),
 'numbers':dict(title='Roupas por números — referência',text='Tamanho;Busto (cm);Cintura (cm);Quadril (cm)\n36;80–84;64–68;88–92\n38;85–88;69–72;93–96\n40;89–92;73–76;97–100\n42;93–96;77–80;101–104\n44;97–100;81–84;105–108\n46;101–104;85–88;109–112'),
 'shoes':dict(title='Calçados — referência BR',text='Numeração BR;Comprimento do pé (cm)\n34;22,5\n35;23\n36;23,5\n37;24,5\n38;25\n39;25,5\n40;26,5\n41;27\n42;27,5\n43;28,5\n44;29'),
 'custom':dict(title='Personalizada',text='Tamanho;Medida (cm)\n')}

def read(raw):
 try:return json.loads(raw or '{}')
 except (ValueError,TypeError):return {}

def details(brand,material,composition,guide,measurements):
 if guide not in ('none',*PRESETS):raise HTTPException(400,'Escolha um guia de medidas válido.')
 values={k:v.strip() for k,v in [('brand',brand),('material',material),('composition',composition)]}
 if any(len(v)>(240 if k=='composition' else 120) for k,v in values.items()):raise HTTPException(400,'Confira os detalhes da peça.')
 text=measurements.strip() or (PRESETS[guide]['text'] if guide in PRESETS else '')
 if len(text)>6000:raise HTTPException(400,'Guia muito longo; use até 6000 caracteres.')
 rows=[line.split(';') for line in text.splitlines() if line.strip()]
 if guide!='none' and (len(rows)<2 or len(rows)>41 or not 2<=len(rows[0])<=6 or any(len(r)!=len(rows[0]) or any(not x.strip() or len(x)>80 for x in r) for r in rows)):
  raise HTTPException(400,'Use cabeçalho e uma linha por tamanho, com 2 a 6 colunas separadas por ponto e vírgula.')
 return dict(**values,guide=guide,measurements=text if guide!='none' else '')

def install(g):
 g['templates'].env.globals.update(fashion_details387=read,fashion_presets387=PRESETS)


def seed_demo(g):
 with g['db']() as c:
  rows=c.execute("SELECT pr.id,pr.name,pr.customization192 FROM products pr JOIN professionals p ON p.id=pr.professional_id WHERE p.slug IN ('nowup-moda-demonstracao','nowup-moda-modelo') AND p.is_demo=1 AND pr.fashion_details387='{}'").fetchall()
  for row in rows:
   groups=read(row['customization192']).get('groups',[])
   size=next((x for x in groups if x.get('id')=='fashionSize385'),None)
   guide='letters' if size and size['name']!='Numeração' else 'shoes' if size else 'none'
   c.execute('UPDATE products SET fashion_details387=? WHERE id=?',(json.dumps(details('','','',guide,''),ensure_ascii=False),row['id']))

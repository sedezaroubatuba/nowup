"""Curated delivery names from Ubatuba municipal district maps (Plano Diretor 2022).
Source: https://planodiretor.ubatuba.sp.gov.br/mapas/
Names only: no coordinate, street or polygon containment verification.
"""
import re, unicodedata
SOURCE='https://planodiretor.ubatuba.sp.gov.br/mapas/'
NAMES=tuple(sorted('''Acaraú|Almada|Barra da Lagoa|Barra Seca|Bela Vista|Camburi|Casanga|Centro|Corcovado|Domingas Dias|Enseada|Estufa I|Estufa II|Figueira|Flamengo|Folha Seca|Horto|Ipiranguinha|Itaguá|Itamambuca|Jardim Ubatuba|Lagoinha|Lázaro|Marafunda|Maranduba|Mato Dentro|Monte Valério|Pedra Verde|Pedreira|Perequê-Açu|Perequê-Mirim|Picinguaba|Ponta Grossa|Praia da Caçandoca|Praia da Fazenda|Praia da Fortaleza|Praia da Ponta Aguda|Praia do Félix|Praia do Frade|Praia do Sapé|Praia Grande|Praia Grande do Bonete|Praia Vermelha|Praia Vermelha do Norte|Praia Vermelha do Sul|Prumirim|Puruba|Ressaca|Rio da Prata|Rio Escuro|Saco da Ribeira|Santa Rita|Sertão da Quina|Sertão do Araribá|Sertão do Engenho Velho|Sertão do Ingá|Sertão do Meio|Sertão do Perequê-Mirim|Sertão do Puruba|Sertão do Ubatumirim|Sesmaria|Silop|Sumaré|Tabatinga|Taquaral|Tenório|Toninhas|Ubatumirim|Umuarama'''.split('|')))
def key(value):
    return ' '.join(re.sub(r'[^a-z0-9 ]',' ',''.join(c for c in unicodedata.normalize('NFD',str(value or '').lower()) if not unicodedata.combining(c))).split())
ALIASES={key(n):n for n in NAMES}
ALIASES.update({key(a):b for a,b in {'Estufa 1':'Estufa I','Estufa 2':'Estufa II','Promirim':'Prumirim','Silope':'Silop','Pereque Acu':'Perequê-Açu','Pereque Mirim':'Perequê-Mirim','Praia do Itamambuca':'Itamambuca','Felix':'Praia do Félix','Sapé':'Praia do Sapé','Fortaleza':'Praia da Fortaleza','Caçandoca':'Praia da Caçandoca'}.items()})
def names(city):return NAMES if key(city)=='ubatuba' else ()
def canonical(city,value):return ALIASES.get(key(value)) if names(city) else None

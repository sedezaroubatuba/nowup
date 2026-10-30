"""Store-owned complementary products; prices remain validated by checkout."""
from fastapi import HTTPException

def validate_pairs(conn, store_id, values, product_id=None):
    ids=list(dict.fromkeys(values))
    if len(ids)>20:
        raise HTTPException(400,"Escolha no máximo 20 produtos combináveis.")
    for value in ids:
        if value==product_id or not conn.execute("SELECT id FROM products WHERE id=? AND professional_id=?",(value,store_id)).fetchone():
            raise HTTPException(400,"Selecione produtos diferentes, pertencentes à sua loja.")
    return ",".join(str(value) for value in ids)

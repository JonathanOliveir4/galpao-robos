from sqlalchemy import select

from .config import ALTURA, LARGURA
from .models import Estoque, Galpao, Posicao, Produto, Robo, Setor


def _tipo(x, y):
    if y == 0 and x <= 2:
        return "doca"
    if (x, y) in ((19, 0), (0, 19), (19, 19)):
        return "carregador"
    if y in (4, 5, 10, 11, 15, 16) and 2 <= x <= 17 and x not in (9, 10):
        return "prateleira"
    return "corredor"


def seed(db):
    if db.scalar(select(Galpao)):
        return
    g = Galpao(nome="Galpão 1", largura=LARGURA, altura=ALTURA)
    db.add(g)
    db.flush()
    setores = {n: Setor(galpao_id=g.id, nome=n) for n in "ABC"}
    db.add_all(setores.values())
    db.flush()

    prateleiras = []
    for y in range(ALTURA):
        for x in range(LARGURA):
            t = _tipo(x, y)
            setor = setores["A" if y < 8 else "B" if y < 13 else "C"]
            p = Posicao(galpao_id=g.id, setor_id=setor.id, x=x, y=y, z=0, tipo=t,
                        codigo=f"{t[0].upper()}-{x:02d}-{y:02d}")
            db.add(p)
            if t == "prateleira":
                prateleiras.append(p)
    db.flush()

    produtos = [
        Produto(sku="PAR-001", nome="Parafuso M8 (cx)", peso_kg=2.0),
        Produto(sku="MOT-010", nome="Motor DC 12V", peso_kg=1.2),
        Produto(sku="PLC-100", nome="Placa controladora", peso_kg=0.4, fragil=True),
        Produto(sku="SEN-020", nome="Sensor ultrassônico", peso_kg=0.1, fragil=True),
        Produto(sku="CAB-050", nome="Rolo de cabo 50m", peso_kg=3.5),
    ]
    db.add_all(produtos)
    db.flush()

    prateleiras.sort(key=lambda p: (p.y, p.x))
    for i, p in enumerate(prateleiras[::7]):
        db.add(Estoque(produto_id=produtos[i % len(produtos)].id, posicao_id=p.id, quantidade=10))

    for i in range(3):
        db.add(Robo(id=f"R{i + 1:02d}", x=i, y=0, bateria=100.0, status="disponivel"))
    db.commit()

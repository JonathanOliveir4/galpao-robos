import threading

from sqlalchemy import select

from .config import BATERIA_POR_CELULA, MARGEM_BATERIA
from .models import Galpao, LogMovimentacao, OrdemServico, Posicao, Robo, agora
from .mqtt_client import bus
from .pathfinding import astar
from .ws import manager

_lock = threading.Lock()


def tentar_despachar(db, ordem: OrdemServico) -> bool:
    """Escolhe o robô disponível mais próximo da origem com bateria suficiente
    para a rota completa (robô -> origem -> destino) e envia o comando via MQTT."""
    with _lock:
        db.refresh(ordem)
        if ordem.status != "pendente":
            return False
        origem = db.get(Posicao, ordem.origem_id)
        destino = db.get(Posicao, ordem.destino_id)
        galpao = db.scalars(select(Galpao)).first()
        bloqueios = {(p.x, p.y) for p in db.scalars(select(Posicao).where(Posicao.tipo == "prateleira"))}
        o, d = (origem.x, origem.y), (destino.x, destino.y)

        melhor = None
        for r in db.scalars(select(Robo).where(Robo.status == "disponivel")):
            seg1 = astar((r.x, r.y), o, bloqueios, galpao.largura, galpao.altura)
            seg2 = astar(o, d, bloqueios, galpao.largura, galpao.altura)
            if seg1 is None or seg2 is None:
                continue
            rota = seg1 + seg2[1:]
            custo = (len(rota) - 1) * BATERIA_POR_CELULA + MARGEM_BATERIA
            if r.bateria < custo:
                continue
            if melhor is None or len(seg1) < melhor[2]:
                melhor = (r, rota, len(seg1))
        if melhor is None:
            return False

        robo, rota, n1 = melhor
        ordem.status = "em_andamento"
        ordem.robo_id = robo.id
        robo.status = "em_transito"
        robo.despachado_em = agora()
        db.add(LogMovimentacao(tipo="despacho", robo_id=robo.id, ordem_id=ordem.id,
                               produto_id=ordem.produto_id, x=robo.x, y=robo.y,
                               detalhe=f"rota com {len(rota)} células"))
        db.commit()

        bus.publish_comando(robo.id, {
            "ordem_id": ordem.id,
            "rota": [list(p) for p in rota],
            "pickup_idx": n1 - 1,
        })
        manager.broadcast({"tipo": "ordem", "id": ordem.id, "status": ordem.status, "robo_id": robo.id})
        manager.broadcast({"tipo": "robo", "id": robo.id, "x": robo.x, "y": robo.y,
                           "bateria": robo.bateria, "status": robo.status})
        return True


def despachar_pendentes(db):
    pendentes = db.scalars(select(OrdemServico).where(OrdemServico.status == "pendente")
                           .order_by(OrdemServico.id)).all()
    for ordem in pendentes:
        if not tentar_despachar(db, ordem):
            break

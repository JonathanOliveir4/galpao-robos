from datetime import timedelta

from sqlalchemy import select

from .database import SessionLocal
from .dispatcher import despachar_pendentes
from .models import Estoque, LogMovimentacao, OrdemServico, Robo, agora
from .ws import manager

GRACA_DESPACHO = timedelta(seconds=5)


def _concluir(db, ordem: OrdemServico):
    def slot(posicao_id):
        return db.scalar(select(Estoque).where(Estoque.produto_id == ordem.produto_id,
                                               Estoque.posicao_id == posicao_id))
    orig = slot(ordem.origem_id)
    if orig:
        orig.quantidade = max(0, orig.quantidade - ordem.quantidade)
        if orig.quantidade == 0:
            db.delete(orig)
    dest = slot(ordem.destino_id)
    if dest:
        dest.quantidade += ordem.quantidade
    else:
        db.add(Estoque(produto_id=ordem.produto_id, posicao_id=ordem.destino_id,
                       quantidade=ordem.quantidade))
    ordem.status = "concluida"
    ordem.concluido_em = agora()


def on_mqtt_message(robo_id: str, data: dict):
    """Chamado pela thread do MQTT a cada mensagem em robo/<id>/status."""
    evento = data.get("evento")
    with SessionLocal() as db:
        robo = db.get(Robo, robo_id)
        if robo is None:
            robo = Robo(id=robo_id)
            db.add(robo)
        robo.x, robo.y = data["x"], data["y"]
        robo.bateria = data["bateria"]

        # Evita que um heartbeat "disponivel" enviado antes de o robô receber o comando
        # desfaça o despacho recém-feito.
        recem_despachado = (robo.despachado_em is not None
                            and agora() - robo.despachado_em.astimezone(agora().tzinfo) < GRACA_DESPACHO)
        if not (data["status"] == "disponivel" and robo.status == "em_transito"
                and evento is None and recem_despachado):
            robo.status = data["status"]

        ordem = db.get(OrdemServico, data["ordem_id"]) if data.get("ordem_id") else None
        if evento == "coleta" and ordem:
            db.add(LogMovimentacao(tipo="coleta", robo_id=robo_id, ordem_id=ordem.id,
                                   produto_id=ordem.produto_id, x=robo.x, y=robo.y))
        if evento == "entrega_concluida" and ordem and ordem.status != "concluida":
            _concluir(db, ordem)
            db.add(LogMovimentacao(tipo="entrega", robo_id=robo_id, ordem_id=ordem.id,
                                   produto_id=ordem.produto_id, x=robo.x, y=robo.y))
            manager.broadcast({"tipo": "ordem", "id": ordem.id, "status": "concluida", "robo_id": robo_id})
        db.commit()

        if robo.status == "disponivel":
            despachar_pendentes(db)
            db.refresh(robo)

        manager.broadcast({"tipo": "robo", "id": robo.id, "x": robo.x, "y": robo.y,
                           "bateria": round(robo.bateria, 1), "status": robo.status})

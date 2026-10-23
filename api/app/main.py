import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select

from .database import Base, SessionLocal, engine, get_db
from .dispatcher import tentar_despachar
from .models import Estoque, Galpao, LogMovimentacao, OrdemServico, Posicao, Produto, Robo
from .mqtt_client import bus
from .seed import seed
from .services import on_mqtt_message
from .ws import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    manager.loop = asyncio.get_running_loop()
    bus.start(on_mqtt_message)
    yield
    bus.stop()


app = FastAPI(title="Galpão 4.0", lifespan=lifespan)


class OrdemIn(BaseModel):
    produto_id: int
    origem_id: int
    destino_id: int
    quantidade: int = Field(1, gt=0)


class ProdutoIn(BaseModel):
    sku: str
    nome: str
    peso_kg: float = 1.0
    fragil: bool = False


def _ordem(o: OrdemServico):
    return {"id": o.id, "produto_id": o.produto_id, "origem_id": o.origem_id,
            "destino_id": o.destino_id, "quantidade": o.quantidade,
            "robo_id": o.robo_id, "status": o.status}


def _robo(r: Robo):
    return {"id": r.id, "x": r.x, "y": r.y, "bateria": round(r.bateria, 1), "status": r.status}


@app.get("/mapa")
def mapa(db=Depends(get_db)):
    g = db.scalars(select(Galpao)).first()
    por_pos = {}
    for e, p in db.execute(select(Estoque, Produto).join(Produto, Produto.id == Estoque.produto_id)):
        por_pos.setdefault(e.posicao_id, []).append(
            {"produto_id": p.id, "nome": p.nome, "qtd": e.quantidade})
    posicoes = [{"id": p.id, "codigo": p.codigo, "x": p.x, "y": p.y, "tipo": p.tipo,
                 "estoque": por_pos.get(p.id, [])}
                for p in db.scalars(select(Posicao).order_by(Posicao.y, Posicao.x))]
    return {"largura": g.largura, "altura": g.altura, "posicoes": posicoes}


@app.get("/robos")
def robos(db=Depends(get_db)):
    return [_robo(r) for r in db.scalars(select(Robo).order_by(Robo.id))]


@app.get("/produtos")
def produtos(db=Depends(get_db)):
    return [{"id": p.id, "sku": p.sku, "nome": p.nome, "peso_kg": p.peso_kg, "fragil": p.fragil}
            for p in db.scalars(select(Produto))]


@app.post("/produtos", status_code=201)
def criar_produto(body: ProdutoIn, db=Depends(get_db)):
    p = Produto(**body.model_dump())
    db.add(p)
    db.commit()
    return {"id": p.id}


@app.get("/ordens")
def ordens(db=Depends(get_db)):
    return [_ordem(o) for o in db.scalars(select(OrdemServico).order_by(OrdemServico.id.desc()).limit(50))]


@app.post("/ordens", status_code=201)
def criar_ordem(body: OrdemIn, db=Depends(get_db)):
    if body.origem_id == body.destino_id:
        raise HTTPException(400, "origem e destino devem ser diferentes")
    origem, destino = db.get(Posicao, body.origem_id), db.get(Posicao, body.destino_id)
    if not (db.get(Produto, body.produto_id) and origem and destino):
        raise HTTPException(404, "produto ou posição inexistente")
    est = db.scalar(select(Estoque).where(Estoque.produto_id == body.produto_id,
                                          Estoque.posicao_id == body.origem_id))
    if not est or est.quantidade < body.quantidade:
        raise HTTPException(409, "estoque insuficiente na posição de origem")
    ordem = OrdemServico(**body.model_dump())
    db.add(ordem)
    db.commit()
    tentar_despachar(db, ordem)   # sem robô livre, a ordem fica pendente e é despachada depois
    db.refresh(ordem)
    manager.broadcast({"tipo": "ordem", "id": ordem.id, "status": ordem.status})
    return _ordem(ordem)


@app.get("/logs")
def logs(db=Depends(get_db)):
    q = select(LogMovimentacao).order_by(LogMovimentacao.id.desc()).limit(100)
    return [{"id": l.id, "timestamp": l.timestamp, "tipo": l.tipo, "robo_id": l.robo_id,
             "ordem_id": l.ordem_id, "x": l.x, "y": l.y, "detalhe": l.detalhe}
            for l in db.scalars(q)]


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.conectar(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.desconectar(ws)


app.mount("/", StaticFiles(directory="dashboard", html=True), name="dashboard")

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError

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


app = FastAPI(title="Galpão 4.0", version="2.0.0", lifespan=lifespan)


class OrdemIn(BaseModel):
    produto_id: int
    origem_id: int
    destino_id: int
    quantidade: int = Field(1, gt=0)


class ProdutoIn(BaseModel):
    sku: str = Field(min_length=1, max_length=30)
    nome: str = Field(min_length=1, max_length=100)
    peso_kg: float = Field(default=1.0, gt=0)
    fragil: bool = False


class ProdutoUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=30)
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    peso_kg: float | None = Field(default=None, gt=0)
    fragil: bool | None = None


class EstoqueIn(BaseModel):
    produto_id: int
    posicao_id: int
    quantidade: int = Field(ge=0)


def _ordem(o: OrdemServico):
    return {"id": o.id, "produto_id": o.produto_id, "origem_id": o.origem_id,
            "destino_id": o.destino_id, "quantidade": o.quantidade,
            "robo_id": o.robo_id, "status": o.status}


def _robo(r: Robo):
    return {"id": r.id, "x": r.x, "y": r.y, "bateria": round(r.bateria, 1), "status": r.status}


def _produto(p: Produto):
    return {"id": p.id, "sku": p.sku, "nome": p.nome, "peso_kg": p.peso_kg, "fragil": p.fragil}


@app.get("/health")
def health():
    return {"status": "ok", "database": "MySQL"}


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


@app.get("/posicoes")
def listar_posicoes(db=Depends(get_db)):
    return [{"id": p.id, "codigo": p.codigo, "x": p.x, "y": p.y, "tipo": p.tipo}
            for p in db.scalars(select(Posicao).order_by(Posicao.codigo))]


@app.get("/robos")
def robos(db=Depends(get_db)):
    return [_robo(r) for r in db.scalars(select(Robo).order_by(Robo.id))]


@app.get("/produtos")
def produtos(db=Depends(get_db)):
    return [_produto(p) for p in db.scalars(select(Produto).order_by(Produto.id))]


@app.post("/produtos", status_code=201)
def criar_produto(body: ProdutoIn, db=Depends(get_db)):
    p = Produto(**body.model_dump())
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe um produto com esse SKU")
    db.refresh(p)
    return _produto(p)


@app.put("/produtos/{produto_id}")
def atualizar_produto(produto_id: int, body: ProdutoUpdate, db=Depends(get_db)):
    p = db.get(Produto, produto_id)
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(p, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "SKU já cadastrado para outro produto")
    db.refresh(p)
    return _produto(p)


@app.delete("/produtos/{produto_id}", status_code=204)
def excluir_produto(produto_id: int, db=Depends(get_db)):
    p = db.get(Produto, produto_id)
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    if db.scalar(select(Estoque).where(Estoque.produto_id == produto_id)):
        raise HTTPException(409, "Não é possível excluir: produto possui estoque")
    if db.scalar(select(OrdemServico).where(OrdemServico.produto_id == produto_id)):
        raise HTTPException(409, "Não é possível excluir: produto possui ordens vinculadas")
    db.delete(p)
    db.commit()


@app.get("/estoque")
def listar_estoque(db=Depends(get_db)):
    linhas = db.execute(select(Estoque, Produto, Posicao)
                        .join(Produto, Produto.id == Estoque.produto_id)
                        .join(Posicao, Posicao.id == Estoque.posicao_id)
                        .order_by(Produto.nome, Posicao.codigo))
    return [{"id": e.id, "produto_id": p.id, "sku": p.sku, "produto": p.nome,
             "posicao_id": pos.id, "posicao": pos.codigo, "quantidade": e.quantidade}
            for e, p, pos in linhas]


@app.post("/estoque", status_code=201)
def criar_ou_atualizar_estoque(body: EstoqueIn, db=Depends(get_db)):
    if not db.get(Produto, body.produto_id):
        raise HTTPException(404, "Produto não encontrado")
    pos = db.get(Posicao, body.posicao_id)
    if not pos or pos.tipo != "prateleira":
        raise HTTPException(400, "A posição precisa ser uma prateleira válida")
    registro = db.scalar(select(Estoque).where(Estoque.produto_id == body.produto_id,
                                  Estoque.posicao_id == body.posicao_id))
    if registro and body.quantidade == 0:
        db.delete(registro)
        db.commit()
        return {"mensagem": "Estoque zerado e registro removido"}
    if registro:
        registro.quantidade = body.quantidade
    elif body.quantidade > 0:
        registro = Estoque(**body.model_dump())
        db.add(registro)
    else:
        raise HTTPException(400, "Informe uma quantidade maior que zero para novo estoque")
    db.commit()
    db.refresh(registro)
    return {"id": registro.id, "produto_id": registro.produto_id,
            "posicao_id": registro.posicao_id, "quantidade": registro.quantidade}


@app.put("/estoque/{estoque_id}")
def atualizar_estoque(estoque_id: int, quantidade: int = Query(..., ge=0), db=Depends(get_db)):
    registro = db.get(Estoque, estoque_id)
    if not registro:
        raise HTTPException(404, "Registro de estoque não encontrado")
    registro.quantidade = quantidade
    if quantidade == 0:
        db.delete(registro)
        db.commit()
        return {"mensagem": "Estoque zerado e registro removido"}
    db.commit()
    return {"id": registro.id, "quantidade": registro.quantidade}


@app.delete("/estoque/{estoque_id}", status_code=204)
def excluir_estoque(estoque_id: int, db=Depends(get_db)):
    registro = db.get(Estoque, estoque_id)
    if not registro:
        raise HTTPException(404, "Registro de estoque não encontrado")
    db.delete(registro)
    db.commit()


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
    tentar_despachar(db, ordem)
    db.refresh(ordem)
    manager.broadcast({"tipo": "ordem", "id": ordem.id, "status": ordem.status})
    return _ordem(ordem)


@app.get("/logs")
def logs(db=Depends(get_db)):
    q = select(LogMovimentacao).order_by(LogMovimentacao.id.desc()).limit(100)
    return [{"id": l.id, "timestamp": l.timestamp, "tipo": l.tipo, "robo_id": l.robo_id,
             "ordem_id": l.ordem_id, "x": l.x, "y": l.y, "detalhe": l.detalhe}
            for l in db.scalars(q)]


@app.get("/analise/resumo")
def analise_resumo(db=Depends(get_db)):
    """Indicadores calculados sobre os dados públicos importados da ANTT/CIOT."""
    try:
        existe = db.execute(text("""SELECT COUNT(*) FROM information_schema.tables
                                  WHERE table_schema='analise_logistica'
                                  AND table_name='ciot_mensal'""")).scalar_one()
        if not existe:
            return {"disponivel": False, "mensagem": "Importe o CSV da ANTT na tabela analise_logistica.ciot_mensal."}
        row = db.execute(text("""SELECT COUNT(*) AS registros,
            COALESCE(SUM(quantidade_ciots),0) AS total_ciots,
            COALESCE(MAX(quantidade_ciots),0) AS max_ciots,
            COALESCE(MIN(quantidade_ciots),0) AS min_ciots,
            COALESCE(AVG(quantidade_ciots),0) AS media_ciots,
            COALESCE(SUM(quantidade_trc),0) AS total_transportadores
            FROM analise_logistica.ciot_mensal""")).mappings().one()
        rotas = db.execute(text("""SELECT municipio_origem, uf_origem, municipio_destino,
            uf_destino, SUM(quantidade_ciots) AS total_ciots
            FROM analise_logistica.ciot_mensal
            GROUP BY municipio_origem, uf_origem, municipio_destino, uf_destino
            ORDER BY total_ciots DESC LIMIT 8""")).mappings().all()
        return {"disponivel": True, "indicadores": dict(row), "rotas": [dict(r) for r in rotas]}
    except OperationalError:
        return {"disponivel": False, "mensagem": "Schema analise_logistica ainda não foi inicializado. Consulte o README."}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.conectar(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.desconectar(ws)


app.mount("/", StaticFiles(directory="dashboard", html=True), name="dashboard")

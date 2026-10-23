from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def agora():
    return datetime.now(timezone.utc)


class Galpao(Base):
    __tablename__ = "galpao"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    largura: Mapped[int]
    altura: Mapped[int]


class Setor(Base):
    __tablename__ = "setor"
    id: Mapped[int] = mapped_column(primary_key=True)
    galpao_id: Mapped[int] = mapped_column(ForeignKey("galpao.id"))
    nome: Mapped[str] = mapped_column(String(50))


class Posicao(Base):
    """Célula do mapa. tipo: corredor | prateleira | doca | carregador"""
    __tablename__ = "posicao"
    __table_args__ = (UniqueConstraint("galpao_id", "x", "y", "z"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    galpao_id: Mapped[int] = mapped_column(ForeignKey("galpao.id"))
    setor_id: Mapped[int | None] = mapped_column(ForeignKey("setor.id"), nullable=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    x: Mapped[int]
    y: Mapped[int]
    z: Mapped[int] = mapped_column(default=0)
    tipo: Mapped[str] = mapped_column(String(20))


class Produto(Base):
    __tablename__ = "produto"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(30), unique=True)
    nome: Mapped[str] = mapped_column(String(100))
    peso_kg: Mapped[float] = mapped_column(Float, default=1.0)
    comprimento_cm: Mapped[float] = mapped_column(Float, default=10)
    largura_cm: Mapped[float] = mapped_column(Float, default=10)
    altura_cm: Mapped[float] = mapped_column(Float, default=10)
    fragil: Mapped[bool] = mapped_column(Boolean, default=False)


class Estoque(Base):
    __tablename__ = "estoque"
    __table_args__ = (UniqueConstraint("produto_id", "posicao_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"))
    posicao_id: Mapped[int] = mapped_column(ForeignKey("posicao.id"))
    quantidade: Mapped[int] = mapped_column(default=0)


class Robo(Base):
    """status: disponivel | em_transito | manutencao"""
    __tablename__ = "robo"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="disponivel")
    bateria: Mapped[float] = mapped_column(Float, default=100.0)
    x: Mapped[int] = mapped_column(default=0)
    y: Mapped[int] = mapped_column(default=0)
    despachado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrdemServico(Base):
    """status: pendente | em_andamento | concluida"""
    __tablename__ = "ordem_servico"
    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"))
    origem_id: Mapped[int] = mapped_column(ForeignKey("posicao.id"))
    destino_id: Mapped[int] = mapped_column(ForeignKey("posicao.id"))
    quantidade: Mapped[int] = mapped_column(default=1)
    robo_id: Mapped[str | None] = mapped_column(ForeignKey("robo.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LogMovimentacao(Base):
    """Auditoria: despacho, coleta, entrega, ..."""
    __tablename__ = "log_movimentacao"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    tipo: Mapped[str] = mapped_column(String(30))
    robo_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ordem_id: Mapped[int | None] = mapped_column(nullable=True)
    produto_id: Mapped[int | None] = mapped_column(nullable=True)
    x: Mapped[int | None] = mapped_column(nullable=True)
    y: Mapped[int | None] = mapped_column(nullable=True)
    detalhe: Mapped[str | None] = mapped_column(String(200), nullable=True)

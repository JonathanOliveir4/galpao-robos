import asyncio

from fastapi import WebSocket


class Manager:
    def __init__(self):
        self.conexoes: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    async def conectar(self, ws: WebSocket):
        await ws.accept()
        self.conexoes.add(ws)

    def desconectar(self, ws: WebSocket):
        self.conexoes.discard(ws)

    async def _enviar(self, msg: dict):
        for ws in list(self.conexoes):
            try:
                await ws.send_json(msg)
            except Exception:
                self.conexoes.discard(ws)

    def broadcast(self, msg: dict):
        """Pode ser chamado de threads (ex.: callback do MQTT)."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._enviar(msg), self.loop)


manager = Manager()

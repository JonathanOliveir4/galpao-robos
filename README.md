# Galpão 4.0 – gerenciamento de estoque com robôs autônomos

Backend FastAPI + PostgreSQL + MQTT (Mosquitto) + simulador de robôs + dashboard (gêmeo digital).

## Rodar
```bash
docker compose up --build
```
Abra http://localhost:8000 (dashboard) e http://localhost:8000/docs (API).
No dashboard: clique numa prateleira laranja (origem) e depois em outra prateleira (destino).

## Contrato MQTT
- `robo/<id>/comando` (backend → robô): `{"ordem_id": 1, "rota": [[x,y],...], "pickup_idx": 7}`
- `robo/<id>/status` (robô → backend): `{"x","y","bateria","status","ordem_id","evento"}`
  com `evento` = `null` | `"coleta"` | `"entrega_concluida"`.

## Fluxo
Ordem criada → despacho do robô disponível mais próximo com bateria suficiente → rota A* publicada →
robô anda e publica posição → backend grava logs/estoque e repassa ao dashboard por WebSocket.

## Estrutura
- `api/app/models.py` – tabelas (Galpao, Setor, Posicao, Produto, Estoque, Robo, OrdemServico, LogMovimentacao)
- `api/app/pathfinding.py` – A*
- `api/app/dispatcher.py` – escolha do robô + comando MQTT
- `api/app/services.py` – tratamento do status vindo dos robôs
- `simulador/robo.py` – robôs simulados
- `dashboard/index.html` – mapa em tempo real

## Limitações atuais (bons itens de "trabalhos futuros")
- Sem prevenção de colisão entre robôs (próximo passo: reserva de células por instante de tempo).
- Sem reserva de estoque (duas ordens podem disputar o mesmo item).
- Recarga é simplificada (bateria sobe com o robô parado, sem ir ao carregador).
- CRUD completo (posições, estoque, robôs) ainda não exposto na API.
- Sem autenticação; Mosquitto aceita conexões anônimas.

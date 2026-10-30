# Galpão 4.0 — gerenciamento de estoque com robôs autônomos

Projeto integrado de Engenharia de Software e Banco de Dados: FastAPI + MySQL 8.4 + MQTT/Mosquitto + simulador de robôs + dashboard web.

## 1. Arquitetura e bancos

O MySQL hospeda dois schemas independentes:

- `galpao`: banco transacional do sistema (galpão, setores, posições, produtos, estoque, robôs, ordens e logs).
- `analise_logistica`: banco analítico com dados públicos da ANTT sobre o Código Identificador da Operação de Transporte (CIOT).

A API usa o schema `galpao`. As consultas analíticas leem `analise_logistica.ciot_mensal`.

## 2. Executar o projeto

Na pasta que contém `docker-compose.yml`:

```powershell
docker compose up --build
```

Acesse:

- Dashboard: http://localhost:8000
- Documentação interativa da API: http://localhost:8000/docs
- Verificação da API: http://localhost:8000/health

Serviços/portas:

- FastAPI: `localhost:8000`
- MySQL: `localhost:3307` (porta interna do container: 3306)
- MQTT: `localhost:1883`

Credenciais locais de desenvolvimento: usuário `galpao`, senha `galpao`; root: `root`. Não reutilize essas credenciais em produção.

## 3. Banco de dados e acesso SQL

Entrar no MySQL:

```powershell
docker compose exec db mysql -ugalpao -pgalpao
```

Listar schemas e tabelas:

```sql
SHOW DATABASES;
USE galpao;
SHOW TABLES;
USE analise_logistica;
SHOW TABLES;
```

O Compose publica o MySQL na porta `3307`. No MySQL Workbench/DBeaver, use host `127.0.0.1`, porta `3307`, usuário `galpao`, senha `galpao`.

**Volumes existentes:** os scripts em `mysql/init` são executados automaticamente somente na primeira criação do volume MySQL. Se o volume já existia antes da criação do schema analítico, execute manualmente:

```powershell
docker compose exec db mysql -uroot -proot -e "CREATE DATABASE IF NOT EXISTS analise_logistica CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL PRIVILEGES ON analise_logistica.* TO 'galpao'@'%';"
Get-Content -Raw mysql/init/02-ciot-table.sql | docker compose exec -T db mysql -ugalpao -pgalpao analise_logistica
```

Não use `docker compose down -v` sem querer apagar todos os dados persistidos.

## 4. Dados públicos — ANTT / CIOT

Fonte: Agência Nacional de Transportes Terrestres (ANTT), conjunto **Código identificador da operação de transporte — CIOT**:

https://dados.antt.gov.br/dataset/ciot

Recurso CSV de setembro de 2026 (arquivo de aproximadamente 35 MB):
https://dados.antt.gov.br/dataset/4f063df4-e2cc-41f3-8e2a-41dbea80db6f/resource/7372a7e6-d046-483a-8d42-7d4d290a96bd/download/09_2026_ciots.csv

O conjunto apresenta quantidade de CIOTs emitidos e os campos de município/UF de origem e destino, NCM da carga, quantidade de CIOTs, transportadores e contratantes. Consulte o dicionário de dados disponível na mesma página. A base é atualizada mensalmente e cada recurso representa um período mensal.

### Preparar os arquivos CSV

1. Acesse o conjunto de dados da ANTT acima.
2. Baixe os recursos mensais no formato CSV.
3. Crie a pasta `dados_publicos/ciot_mensal/`.
4. Coloque os arquivos nela e renomeie cada um para `AAAA-MM.csv` (ex.: `2026-09.csv`). Preserve os nomes das colunas originais definidos no dicionário da ANTT.
5. Execute:

```powershell
python tools/preparar_ciot_csv.py
```

O script gera `dados_publicos/ciot_mensal_consolidado.csv`, acrescentando a coluna `mes_referencia` para permitir análise temporal. O arquivo modelo de cabeçalho está em `dados_publicos/ciot_modelo.csv`.

### Importar no MySQL Workbench

1. Conecte ao MySQL em `127.0.0.1:3307`.
2. Selecione o schema `analise_logistica`.
3. Use **Table Data Import Wizard** e escolha `dados_publicos/ciot_mensal_consolidado.csv`.
4. Importe para a tabela existente `ciot_mensal` (não crie outra tabela). Confira o mapeamento das nove colunas.
5. Valide com `SELECT COUNT(*) FROM analise_logistica.ciot_mensal;`.

A tabela e as views `vw_ciot_por_mes` e `vw_top_rotas` são criadas por `mysql/init/02-ciot-table.sql`. A coluna `mes_referencia` deve ser o primeiro dia do mês (AAAA-MM-01).

## 5. Consultas analíticas

O arquivo `sql/analise_logistica.sql` contém consultas prontas com `MAX`, `MIN`, `SUM` e `AVG`, além de:

- volume total de CIOTs;
- evolução mensal das operações;
- principais corredores logísticos (município de origem e destino);
- distribuição por UF de origem;
- natureza de carga (NCM) com maior movimentação.

A análise ajuda a identificar corredores com maior volume de operações e a contextualizar a importância de sistemas de armazenagem, controle de estoque e movimentação logística. Os dados nacionais são contexto setorial; não representam medições do galpão simulado.

## 6. Funcionalidades do Dashboard e API

### Monitoramento

- mapa 2D do galpão;
- posição, bateria e status dos robôs em tempo real via WebSocket;
- ordens de movimentação e atualização do mapa ao concluir uma entrega.

### CRUD de produtos

- `GET /produtos`: listar;
- `POST /produtos`: inserir;
- `PUT /produtos/{id}`: alterar;
- `DELETE /produtos/{id}`: excluir (bloqueia exclusão quando há estoque ou ordens vinculadas).

### CRUD de estoque

- `GET /estoque`: consultar estoque com produto e posição;
- `POST /estoque`: inserir ou atualizar quantidade por produto/posição;
- `PUT /estoque/{id}?quantidade=N`: alterar quantidade;
- `DELETE /estoque/{id}`: remover registro.

### Outros endpoints

- `GET /mapa`, `GET /posicoes`, `GET /robos`, `GET /ordens`, `POST /ordens`, `GET /logs`;
- `GET /analise/resumo`: indicadores e principais rotas da base pública importada.

O Dashboard disponibiliza formulários e tabelas para cadastrar/consultar/alterar/excluir produtos e registros de estoque, além do monitoramento dos robôs e dos indicadores ANTT.

## 7. Modelo Entidade-Relacionamento

Entidades do schema `galpao`:

- `Galpao` 1:N `Setor`;
- `Galpao` 1:N `Posicao`;
- `Setor` 1:N `Posicao`;
- `Produto` 1:N `Estoque`;
- `Posicao` 1:N `Estoque`;
- `Produto` 1:N `OrdemServico`;
- `Posicao` 1:N `OrdemServico` como origem e também como destino;
- `Robo` 1:N `OrdemServico`;
- `LogMovimentacao` armazena IDs de robô, ordem e produto como atributos de auditoria; na implementação atual, esses campos não são chaves estrangeiras.

No schema analítico, `ciot_mensal` armazena registros públicos agregados por mês, rota e NCM. É independente das tabelas operacionais do galpão.

## 8. MQTT

- `robo/<id>/comando` (backend → robô): JSON com `ordem_id`, `rota` e `pickup_idx`.
- `robo/<id>/status` (robô → backend): posição, bateria, status, ordem e evento (`coleta` ou `entrega_concluida`).

Fluxo: ordem criada → despacho do robô disponível → rota A* publicada → robô simulado percorre a rota → API atualiza estoque e logs → Dashboard recebe atualizações por WebSocket.

## 9. Estrutura relevante

- `api/app/models.py`: entidades SQLAlchemy;
- `api/app/main.py`: endpoints REST, CRUD e análise;
- `api/app/services.py`: tratamento dos eventos MQTT;
- `api/app/dispatcher.py` e `pathfinding.py`: despacho e caminho A*;
- `dashboard/index.html`: monitoramento e gerenciamento;
- `mysql/init/`: criação dos schemas e tabela analítica;
- `sql/analise_logistica.sql`: consultas estatísticas;
- `docs_modelo_er.mmd`: diagrama ER em Mermaid (inclui a tabela analítica independente);
- `tools/preparar_ciot_csv.py`: consolidação dos arquivos mensais ANTT.

## 10. Observações

- O CSV oficial precisa ser baixado e importado pelo grupo; o repositório contém o modelo, o esquema e o script de consolidação, não valores inventados.
- O simulador é uma simulação acadêmica, não controla robôs físicos.
- O projeto ainda não implementa autenticação nem prevenção de colisão entre robôs.

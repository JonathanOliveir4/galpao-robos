USE analise_logistica;

-- 1. Visão geral: funções agregadoras exigidas no trabalho.
SELECT
    COUNT(*) AS total_registros,
    SUM(quantidade_ciots) AS total_ciots,
    MAX(quantidade_ciots) AS maior_quantidade_ciots_em_uma_rota_mes,
    MIN(quantidade_ciots) AS menor_quantidade_ciots_em_uma_rota_mes,
    AVG(quantidade_ciots) AS media_ciots_por_registro,
    SUM(quantidade_trc) AS soma_transportadores_registrados
FROM ciot_mensal;

-- 2. Evolução mensal das emissões de CIOT.
SELECT DATE_FORMAT(mes_referencia, '%Y-%m') AS mes,
       SUM(quantidade_ciots) AS total_ciots
FROM ciot_mensal
GROUP BY DATE_FORMAT(mes_referencia, '%Y-%m')
ORDER BY mes;

-- 3. Principais corredores logísticos (origem -> destino).
SELECT municipio_origem, uf_origem, municipio_destino, uf_destino,
       SUM(quantidade_ciots) AS total_ciots,
       AVG(quantidade_ciots) AS media_ciots
FROM ciot_mensal
GROUP BY municipio_origem, uf_origem, municipio_destino, uf_destino
ORDER BY total_ciots DESC
LIMIT 10;

-- 4. Distribuição por UF de origem.
SELECT uf_origem, SUM(quantidade_ciots) AS total_ciots,
       COUNT(*) AS registros, AVG(quantidade_ciots) AS media_ciots
FROM ciot_mensal
GROUP BY uf_origem
ORDER BY total_ciots DESC;

-- 5. Naturezas de carga (NCM de quatro dígitos) com maior movimentação.
SELECT ncm_carga, SUM(quantidade_ciots) AS total_ciots
FROM ciot_mensal
GROUP BY ncm_carga
ORDER BY total_ciots DESC
LIMIT 10;

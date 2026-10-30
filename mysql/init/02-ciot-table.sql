USE analise_logistica;

-- Estrutura baseada no dicionário oficial de dados do CIOT/ANTT.
-- Cada arquivo mensal da ANTT deve receber sua respectiva mes_referencia.
CREATE TABLE IF NOT EXISTS ciot_mensal (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    mes_referencia DATE NOT NULL,
    municipio_origem VARCHAR(100) NOT NULL,
    uf_origem CHAR(2) NOT NULL,
    municipio_destino VARCHAR(100) NOT NULL,
    uf_destino CHAR(2) NOT NULL,
    ncm_carga VARCHAR(4) NULL,
    quantidade_ciots BIGINT UNSIGNED NOT NULL DEFAULT 0,
    quantidade_trc BIGINT UNSIGNED NOT NULL DEFAULT 0,
    quantidade_contratantes BIGINT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    INDEX idx_ciot_mes (mes_referencia),
    INDEX idx_ciot_origem (uf_origem, municipio_origem),
    INDEX idx_ciot_destino (uf_destino, municipio_destino)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE OR REPLACE VIEW vw_ciot_por_mes AS
SELECT mes_referencia,
       SUM(quantidade_ciots) AS total_ciots,
       AVG(quantidade_ciots) AS media_ciots_por_registro,
       MAX(quantidade_ciots) AS max_ciots,
       MIN(quantidade_ciots) AS min_ciots
FROM ciot_mensal
GROUP BY mes_referencia;

CREATE OR REPLACE VIEW vw_top_rotas AS
SELECT municipio_origem, uf_origem, municipio_destino, uf_destino,
       SUM(quantidade_ciots) AS total_ciots,
       AVG(quantidade_ciots) AS media_ciots
FROM ciot_mensal
GROUP BY municipio_origem, uf_origem, municipio_destino, uf_destino;

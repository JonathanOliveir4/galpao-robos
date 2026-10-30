"""Une arquivos mensais do CIOT/ANTT em um CSV único para importação no MySQL.

Coloque os arquivos CSV originais em dados_publicos/ciot_mensal/ e renomeie-os
no padrão AAAA-MM.csv (ex.: 2026-09.csv). O script adiciona mes_referencia.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTA_ENTRADA = ROOT / "dados_publicos" / "ciot_mensal"
ARQUIVO_SAIDA = ROOT / "dados_publicos" / "ciot_mensal_consolidado.csv"
COLUNAS = [
    "municipio_origem", "uf_origem", "municipio_destino", "uf_destino",
    "ncm_carga", "quantidade_ciots", "quantidade_trc", "quantidade_contratantes",
]

PASTA_ENTRADA.mkdir(parents=True, exist_ok=True)
arquivos = sorted(PASTA_ENTRADA.glob("*.csv"))
if not arquivos:
    raise SystemExit(f"Nenhum CSV encontrado em {PASTA_ENTRADA}")

with ARQUIVO_SAIDA.open("w", newline="", encoding="utf-8-sig") as saida:
    writer = csv.DictWriter(saida, fieldnames=["mes_referencia", *COLUNAS])
    writer.writeheader()
    total = 0
    for arquivo in arquivos:
        referencia = arquivo.stem + "-01"
        if len(arquivo.stem) != 7 or arquivo.stem[4] != "-":
            raise SystemExit(f"Nome inválido: {arquivo.name}. Use AAAA-MM.csv")
        with arquivo.open("r", newline="", encoding="utf-8-sig") as entrada:
            amostra = entrada.read(4096)
            entrada.seek(0)
            try:
                delimitador = csv.Sniffer().sniff(amostra, delimiters=";,\t|").delimiter
            except csv.Error:
                delimitador = ";"
            reader = csv.DictReader(entrada, delimiter=delimitador)
            faltantes = [c for c in COLUNAS if c not in (reader.fieldnames or [])]
            if faltantes:
                raise SystemExit(f"{arquivo.name}: colunas ausentes: {', '.join(faltantes)}")
            for linha in reader:
                registro = {c: (linha.get(c) or "").strip() for c in COLUNAS}
                registro["mes_referencia"] = referencia
                writer.writerow(registro)
                total += 1

print(f"Arquivo criado: {ARQUIVO_SAIDA}")
print(f"Registros consolidados: {total}")

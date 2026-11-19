"""Caso sintético e reproduzível. Só é carregado por ação explícita."""
import csv
import json
from pathlib import Path

from utils.dados import preparar_barco, tabela_para_lista, COLUNAS_CARGAS

PASTA = Path(__file__).resolve().parents[1] / "data"


def exemplo():
    barco = preparar_barco(json.loads((PASTA / "exemplo_embarcacao.json").read_text(encoding="utf-8")))
    with (PASTA / "exemplo_cargas.csv").open(encoding="utf-8") as arquivo:
        cargas = tabela_para_lista(list(csv.DictReader(arquivo)), COLUNAS_CARGAS)
    return barco, cargas

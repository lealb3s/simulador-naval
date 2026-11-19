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



def dados_do_exemplo():
    from copy import deepcopy
    barco,cargas=exemplo()
    return {
        "barco":barco, "cargas":cargas, "cargas_inicio":deepcopy(cargas),
        "pendulos":[{"id":"P1","comprimento_m":2.0},{"id":"P2","comprimento_m":2.5}],
        "config_pendulos":{"ang":2.0,"res":.001,"alt":2.5},
        "erros":{"limite_angulo_graus":4.0},
        "configuracoes":[{"massa_kg":250,"quantidade":n,"distancia_m":d,"pendulo_m":l,"y_inicial_m":0.0}
                         for n,d,l in [(1,1.25,2.0),(2,1.0,2.25),(2,1.25,2.5)]],
        "limites_planejamento":{"lim_ang":"4","max_p":"2,5","res_p":"0,001","lim_massa":"250"},
    }

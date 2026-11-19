"""Consulta direta ou interpolação linear dentro da faixa fornecida.

Não realiza extrapolação nem deduz características hidrostáticas apenas de L, B e D.
"""
import numpy as np
from .validacao import ordenar_hidro_tabela, numero

FIELDS = ("calado_m", "km_m", "kb_m", "lcb_m", "lcf_m", "mtc_kgm_por_m")


def consultar(barco, deslocamento_kg):
    numero(deslocamento_kg, "deslocamento", positivo=True)
    tabela = ordenar_hidro_tabela(barco.get("hidro_tabela", []))
    if tabela:
        d = [r["deslocamento_kg"] for r in tabela]
        if deslocamento_kg < d[0] or deslocamento_kg > d[-1]:
            raise ValueError(f"Deslocamento {deslocamento_kg:g} kg fora da faixa hidrostática [{d[0]:g}, {d[-1]:g}] kg; extrapolação proibida")
        result = {"deslocamento_kg":deslocamento_kg, "metodo":"Interpolação linear interna na tabela hidrostática"}
        indice=int(np.searchsorted(d, deslocamento_kg))
        if indice < len(d) and d[indice] == deslocamento_kg:
            result["metodo"]="Ponto tabulado para o deslocamento da condição"
            result.update({k:tabela[indice].get(k) for k in FIELDS})
        else:
            baixo,alto=tabela[indice-1],tabela[indice]
            fracao=(deslocamento_kg-d[indice-1])/(d[indice]-d[indice-1])
            for k in FIELDS:
                a,b=baixo.get(k),alto.get(k)
                result[k]=None if a is None or b is None else a+(b-a)*fracao
        return result
    ref = barco.get("deslocamento_referencia_kg")
    if ref is None or not np.isclose(ref, deslocamento_kg, rtol=1e-10, atol=1e-9):
        raise ValueError("Sem tabela hidrostática correspondente a este deslocamento. Importe a curva ou informe o estado exato")
    return {"deslocamento_kg":deslocamento_kg, "metodo":"Dados hidrostáticos de uma condição única fornecida", **{k:barco.get(k) for k in FIELDS}}


def superficie_livre(barco, deslocamento_kg):
    """FSC (m)=FSM (kg·m)/Δ (kg), se FSM efetivo foi fornecido."""
    fsm = barco.get("fsm_kgm")
    if fsm is None:
        return None
    return numero(fsm, "Momento de superfície livre", nao_negativo=True)/numero(deslocamento_kg, "Deslocamento", positivo=True)


def trim_estatico(carregamento, hidro):
    """Momento longitudinal Δ(LCG-LCB), kg·m; trim por MCT só quando fornecido."""
    lcg, lcb = carregamento.get("lcg_m"), hidro.get("lcb_m")
    if lcg is None or lcb is None:
        return {"momento_trim_kgm":None, "variacao_trim_m":None}
    momento = carregamento["deslocamento_kg"] * (lcg-lcb)
    mtc = hidro.get("mtc_kgm_por_m")
    return {"momento_trim_kgm":momento,"variacao_trim_m":momento/mtc if mtc is not None and mtc > 0 else None}

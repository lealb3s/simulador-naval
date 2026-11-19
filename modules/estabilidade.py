"""GM pequeno ângulo; GZ geométrico apenas na condição de validade do dado.

GM_efetivo=KM-KG-FSC, onde FSC=FSM/Δ. Não vale para grandes ângulos.
"""
import numpy as np
from .hidrostatica import superficie_livre


def avaliar(barco, condicao, hidro):
    kg, km = condicao.get("kg_m"), hidro.get("km_m")
    fsc = superficie_livre(barco, condicao["deslocamento_kg"])
    gm_solido = km-kg if km is not None and kg is not None else None
    gm_efetivo = gm_solido-fsc if gm_solido is not None and fsc is not None else None
    return {"km_m":km,"kg_m":kg,"gm_solido_m":gm_solido,"fsc_m":fsc,"gm_efetivo_m":gm_efetivo}


def gz_adaptada(barco, condicao):
    """Alteração GZ(φ;KG2)=GZ_ref(φ)+(KGref-KG2) sinφ.

    Válida somente para MESMO deslocamento/casco, CG transversal na linha de centro,
    sem correção variável de superfície livre; curva não é recalculada geometricamente.
    """
    curva = barco.get("gz_curva", [])
    dref = barco.get("gz_deslocamento_kg")
    kref = barco.get("gz_kg_referencia_m")
    if not curva or dref is None or kref is None or condicao.get("kg_m") is None:
        raise ValueError("Curva GZ, deslocamento da curva, KG referência e KG atual obrigatórios")
    if not np.isclose(condicao["deslocamento_kg"], dref, rtol=1e-10):
        raise ValueError("Mudança de deslocamento: GZ referência não pode ser transplantada para outra condição")
    if condicao.get("tcg_m") is None or abs(condicao["tcg_m"]) > 1e-10:
        raise ValueError("GZ adaptada exige TCG=0 na condição considerada")
    if barco.get("fsm_kgm") is None or barco["fsm_kgm"] != 0:
        raise ValueError("GZ adaptada exige ausência de superfície livre (FSM=0); FSC constante não válida em grandes ângulos")
    return [{"angulo_graus":p["angulo_graus"],"gz_m":p["gz_m"]+(kref-condicao["kg_m"])*np.sin(np.deg2rad(p["angulo_graus"]))} for p in curva]

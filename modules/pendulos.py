"""Deflexão por pêndulo em regime quase estático: x=L tan(θ).

Não modela balanço do próprio pêndulo; resolução angular atan(r/L).
"""
from math import atan, degrees, radians, tan
from .validacao import numero


def deflexao(comprimento_m, angulo_graus):
    return numero(comprimento_m,"comprimento do pêndulo", positivo=True)*tan(radians(angulo_graus))


def angulo(comprimento_m, deflexao_m):
    return degrees(atan(numero(deflexao_m, "deflexão") / numero(comprimento_m,"comprimento", positivo=True)))


def resolucao_angular(comprimento_m, resolucao_m):
    return degrees(atan(numero(resolucao_m,"resolução", positivo=True)/numero(comprimento_m,"comprimento",positivo=True)))


def comparar(comprimentos, resolucao_m, angulo_graus=None):
    result=[]
    for i, c in enumerate(comprimentos):
        result.append({"Pêndulo":i+1,"Comprimento (m)":c,
                       "Resolução angular (°)":resolucao_angular(c,resolucao_m),
                       "Deflexão prevista (m)":deflexao(c,angulo_graus) if angulo_graus is not None else None})
    return result

"""Momentos e comparação de configurações em pequenos ângulos."""
from math import atan, degrees
from .validacao import numero
from .pendulos import deflexao, resolucao_angular


def momento_inclinante(massa_kg, distancia_m, quantidade=1):
    if not numero(quantidade,"quantidade",positivo=True).is_integer():
        raise ValueError("Quantidade de pesos deve ser inteira")
    return numero(massa_kg,"massa",positivo=True)*numero(distancia_m,"distância",nao_negativo=True)*int(numero(quantidade,"quantidade",positivo=True))


def angulo_previsto(momento_kgm, deslocamento_kg, gm_efetivo_m):
    """tanφ=Σmd/(ΔGM); limitada pela hipótese metacêntrica de pequeno ângulo."""
    numero(deslocamento_kg,"deslocamento",positivo=True)
    numero(gm_efetivo_m,"GM efetivo",positivo=True)
    return degrees(atan(momento_kgm / (deslocamento_kg*gm_efetivo_m)))


def comparar(configuracoes, deslocamento_kg=None, gm_efetivo_m=None, boca_m=None,
             comprimento_max_pendulo=None, angulo_max=None, resolucao_m=None):
    saida=[]
    for i,c in enumerate(configuracoes):
        m = momento_inclinante(c["massa_kg"],c["distancia_m"],c["quantidade"])
        inclinacao = angulo_previsto(m, deslocamento_kg, gm_efetivo_m) if deslocamento_kg is not None and gm_efetivo_m is not None and gm_efetivo_m > 0 else None
        problemas=[]
        if boca_m is None: problemas.append("Limite de movimento transversal não informado")
        elif c["distancia_m"] > boca_m: problemas.append("Distância supera a boca")
        if comprimento_max_pendulo is None: problemas.append("Altura disponível do pêndulo não informada")
        elif c["pendulo_m"] > comprimento_max_pendulo: problemas.append("Pêndulo não cabe no espaço informado")
        if inclinacao is None: problemas.append("Falta GM efetivo positivo e/ou deslocamento")
        if angulo_max is None: problemas.append("Limite angular de projeto não informado")
        elif inclinacao is not None and abs(inclinacao) > angulo_max: problemas.append("Ângulo supera limite informado")
        if resolucao_m is None: problemas.append("Resolução de leitura não informada")
        saida.append({"Configuração":i+1, "Massa total (kg)":c["massa_kg"]*c["quantidade"],
                      "Quantidade":c["quantidade"],"Distância (m)":c["distancia_m"],
                      "Momento (kg m)":m,"Inclinação prevista (°)":inclinacao,
                      "Pêndulo (m)":c["pendulo_m"],"GM previsto (m)":gm_efetivo_m,
                      "Resolução angular (°)":resolucao_angular(c["pendulo_m"],resolucao_m) if resolucao_m else None,
                      "Viabilidade":"Não comprovada" if problemas else "Atende aos limites informados (não substitui vistoria)",
                      "Pendências / violações":"; ".join(problemas),
                      "Complexidade operacional":f"{c['quantidade']} peso(s) / {c['quantidade']} movimentação(ões)"})
    return saida

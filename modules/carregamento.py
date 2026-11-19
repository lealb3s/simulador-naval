"""Balanço de massa e momentos no referencial X proa, Y boreste, Z cima.

Usa m_total = m_base + Σm; CG = Σ(m_i r_i)/m_total.
Unidade de massa: kg; coordenadas m; momentos de massa: kg·m.
"""
from .validacao import numero, verificar_carga


def calcular(barco, cargas):
    if barco.get("massa_base_kg") is None:
        raise ValueError("Informe a massa base (casco + itens NÃO cadastrados), em kg")
    base = numero(barco["massa_base_kg"], "massa base", nao_negativo=True)
    seen = set()
    for carga in cargas:
        verificar_carga(carga, barco)
        if carga["id"] in seen:
            raise ValueError("IDs de cargas repetidos")
        seen.add(carga["id"])
    massas = base + sum(c["massa_kg"] for c in cargas)
    numero(massas, "deslocamento", positivo=True)
    result = {"deslocamento_kg": massas, "massa_cargas_kg": sum(c["massa_kg"] for c in cargas)}
    for eixo, key in (("x_m", "lcg_m"), ("y_m", "tcg_m"), ("z_m", "kg_m")):
        if base and barco.get("base_" + eixo) is None:
            result[key] = None
            result["momento_" + eixo] = None
        else:
            momento = base * (barco.get("base_" + eixo) or 0) + sum(c["massa_kg"] * c[eixo] for c in cargas)
            result[key] = momento / massas
            result["momento_" + eixo] = momento
    return result


def sugestao_xyz(barco):
    """Apenas sugestão, NÃO uma posição geométrica comprovada."""
    if any(barco.get(k) is None for k in ("L_m", "B_m", "D_m")):
        raise ValueError("Comprimento, boca e pontal necessários para propor posição")
    return {"x_m":barco["L_m"]/2, "y_m":0.0, "z_m":barco["D_m"]/2}


def momento_deslocamento(cargas_antes, cargas_depois):
    """Somente para MESMOS pesos: ΔΣ(m*y), kg·m."""
    antes = {c["id"]: c for c in cargas_antes}
    depois = {c["id"]: c for c in cargas_depois}
    if antes.keys() != depois.keys():
        raise ValueError("Prova requer mesmo conjunto de pesos; não adicione nem retire cargas")
    for k in antes:
        if antes[k]["massa_kg"] != depois[k]["massa_kg"]:
            raise ValueError("Prova requer massas invariáveis")
        if antes[k]["x_m"] != depois[k]["x_m"] or antes[k]["z_m"] != depois[k]["z_m"]:
            raise ValueError("Na prova simulada, mover exclusivamente em Y")
    return sum(depois[k]["massa_kg"] * (depois[k]["y_m"] - antes[k]["y_m"]) for k in antes)


def base_da_condicao(total, centros, cargas):
    """Reconstrói base sem dupla contagem. Entradas em kg e m, no mesmo referencial."""
    total = numero(total,"Deslocamento global",positivo=True)
    massa = total - sum(c["massa_kg"] for c in cargas)
    if massa < 0:
        raise ValueError("A soma das cargas excede o deslocamento global.")
    resultado = {"massa_base_kg":massa}
    for origem,eixo in (("lcg_m","x_m"),("tcg_m","y_m"),("kg_m","z_m")):
        centro = numero(centros.get(origem),origem)
        momento = total*centro - sum(c["massa_kg"]*c[eixo] for c in cargas)
        if massa == 0 and abs(momento)>1e-8*max(1,abs(total*centro)):
            raise ValueError("Sem massa remanescente, os momentos das cargas devem reproduzir o CG global.")
        resultado["base_"+eixo] = momento/massa if massa else None
    return resultado

"""Domínio do modelo acadêmico. Aplicam-se também os limites do projeto."""
from math import atan, degrees

# Teto deliberado para a aproximação metacêntrica neste simulador.
# IMO MSC.267(85), Anexo 1 §2.4.2: faixa típica da prova, não critério universal.
TETO_MODELO_GRAUS = 4.0


def banda_inicial(tcg_m, gm_m):
    """Banda de equilíbrio (°), casco simétrico, trim pequeno, sem momento externo."""
    if tcg_m is None or gm_m is None or gm_m <= 0:
        return None
    banda = degrees(atan(tcg_m / gm_m))
    return banda if abs(banda) <= TETO_MODELO_GRAUS else None

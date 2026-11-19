"""Erros experimentais explicitamente configurados; não estima vento a partir de uma fórmula empírica."""
import numpy as np
from .validacao import numero


def perturbar(momento_real_kgm, pêndulos, angulo_real_graus, configuracao, rng):
    """Massa/distância medidos são enviesados; vento aplicado como momento fornecido.

    Parâmetros: vies_massa_pct, vies_dist_pct, vies_referencia_m,
    desvio_leitura_m, momento_vento_Nm, g_ms2. Resultados rastreáveis.
    """
    from math import tan, radians
    cfg = configuracao or {}
    mg = (1 + float(cfg.get("vies_massa_pct",0))/100)
    dg = (1 + float(cfg.get("vies_dist_pct",0))/100)
    estimado = momento_real_kgm * mg * dg
    lidos=[]
    for p in pêndulos:
        L=numero(p["comprimento_m"],"comprimento",positivo=True)
        ideal=L*tan(radians(angulo_real_graus))
        ruido=rng.normal(0, float(cfg.get("desvio_leitura_m",0)))
        medido = L * (1 + cfg.get("vies_comprimento_pct", 0) / 100)
        numero(medido, "Comprimento informado com viés", positivo=True)
        leitura = ideal + float(cfg.get("vies_referencia_m",0)) + ruido
        lidos.append({"id":p["id"],"comprimento_real_m":L,"comprimento_m":medido,
                      "deflexao_ideal_m":ideal,"deflexao_m":leitura,"erro_leitura_m":leitura-ideal,
                      "angulo_medido_graus":float(np.rad2deg(np.arctan(leitura/medido)))})
    return estimado,lidos


def diagnosticar(condicoes, leituras, angulo_limite=None):
    avisos=[]
    if any(not r.get("estavel",False) for r in leituras):
        avisos.append(("Leituras sem equilíbrio", "Há registros excluídos do ajuste por falta de confirmação de equilíbrio", "Revisar os patamares antes de processar", "REPETIR"))
    if len([r for r in leituras if r.get("estavel",False)])<8: avisos.append(("Incompleto", "Menos de 8 condições registradas", "Completar sequência e verificar retornos a zero", "REPETIR/CONTINUAR"))
    if not any(l.get("momento_kgm",0)>0 for l in leituras) or not any(l.get("momento_kgm",0)<0 for l in leituras):
        avisos.append(("Distribuição unilateral", "Faltam momentos positivos ou negativos", "Registrar movimentos simétricos para identificar vieses", "REPETIR"))
    indices={r["indice_movimento"] for r in leituras if "indice_movimento" in r and r["indice_movimento"]>0}
    if indices and len(indices)<8:
        avisos.append(("Movimentos sem série completa",f"{len(indices)} movimentos distintos com leitura",
                       "Registrar os patamares de cada movimento e conferir os retornos", "CONTINUAR"))
    primeiro_nao_nulo=next((i for i,r in enumerate(leituras) if abs(r.get("momento_kgm",0))>1e-10),len(leituras))
    if leituras and not any(abs(r.get("momento_kgm",0))<1e-10 for r in leituras[primeiro_nao_nulo+1:]):
        avisos.append(("Retorno a zero ausente", "Sem conferência de referência após a primeira leitura", "Voltar à posição inicial e registrar", "REPETIR"))
    injecoes = [
        ("vies_massa_pct","Massa","A escala dos momentos muda e desloca o GM.","Conferir a massa com instrumento calibrado."),
        ("vies_dist_pct","Distância","O braço declarado altera a inclinação da reta.","Remedir os deslocamentos entre marcas."),
        ("vies_comprimento_pct","Comprimento","A escala das tangentes altera o GM.","Medir do ponto de suspensão à régua."),
        ("vies_referencia_m","Zero","A referência desloca as leituras.","Conferir o zero de cada régua."),
        ("desvio_leitura_m","Leitura aleatória","O ruído aumenta a dispersão das tangentes.","Repetir leituras e verificar o desacordo entre pêndulos."),
        ("sigma_vento_Nm","Vento variável","O momento muda entre os patamares.","Comparar retornos a zero e repetir em condições constantes."),
        ("momento_vento_Nm","Vento constante","O momento externo pode deslocar o intercepto.","Medir o momento externo e conferir o zero."),
        ("interferencia_Nm","Interferência externa","Um momento independente dos pesos altera a banda.","Verificar amarras e contatos antes de repetir."),
        ("fsm_extra_kgm","Superfície livre adicional","O GM observado diminui.","Usar o FSM total medido ou eliminar a superfície livre."),
    ]
    for campo, nome, efeito, correcao in injecoes:
        afetadas = [str(i) for i,l in enumerate(leituras,1) if l.get("cenario",{}).get(campo)]
        if afetadas:
            avisos.append((nome+" simulado", efeito+" Leituras "+", ".join(afetadas), correcao, "REVISAR / REPETIR"))
    minimo=condicoes.get("minimo_angulo_graus")
    if minimo is not None and leituras:
        port=[abs(r.get("angulo_graus",0)) for r in leituras if r.get("momento_kgm",0)<0]
        bore=[abs(r.get("angulo_graus",0)) for r in leituras if r.get("momento_kgm",0)>0]
        if (port and max(port)<minimo) or (bore and max(bore)<minimo):
            avisos.append(("Peso possivelmente insuficiente", "Máxima inclinação inferior ao mínimo declarado por um bordo", "Rever momento, escala, condições de mar e procedimento", "REPLANEJAR/REPETIR"))
    min_def=condicoes.get("minima_deflexao_m")
    if min_def is not None:
        por_pendulo={}
        for leitura in leituras:
            for p in leitura.get("pendulos",[]):
                por_pendulo.setdefault(p["id"],[]).append(abs(p["deflexao_m"]))
        for nome, valores in por_pendulo.items():
            if max(valores)<min_def:
                avisos.append(("Deflexão insuficiente", f"{nome}: máxima leitura menor que mínimo fornecido", "Ajustar comprimento ou momento respeitando limites", "REPLANEJAR"))
    if angulo_limite is None: avisos.append(("Critério ausente", "Limite angular não foi declarado", "Indicar limite aplicável ao projeto", "NÃO AVALIADO"))
    elif any(abs(l.get("angulo_graus",0))>angulo_limite for l in leituras):
        avisos.append(("Ângulo excedido", "Medições além do limite fornecido", "Suspender sequência e reduzir momentos", "SUSPENDER"))
    if len(leituras)>1:
        vals=[l.get("desacordo_pendulos_graus") for l in leituras if l.get("desacordo_pendulos_graus") is not None]
        if vals and condicoes.get("tolerancia_pendulos_graus") is not None and any(x>condicoes["tolerancia_pendulos_graus"] for x in vals):
            avisos.append(("Pêndulos divergentes", "Desacordo acima de tolerância definida", "Rever leitura, referência e comprimentos", "REPETIR"))
    return avisos


def momento_externo(config, passo):
    """Momento imposto em N·m, constante por patamar; semente reproduzível."""
    media = config.get("momento_vento_Nm", 0)
    desvio = config.get("sigma_vento_Nm", 0)
    return float(media + np.random.default_rng(3271 + passo).normal(0, desvio)
                 + config.get("interferencia_Nm", 0))


def diagnostico_detalhado(condicoes, leituras, limite=None):
    """Diagnóstico rastreável, organizado por efeito, checagem e decisão."""
    registros=[]
    for titulo,efeito,correcao,decisao in diagnosticar(condicoes,leituras,limite):
        causas={
            "Incompleto":"Quantidade de patamares insuficiente",
            "Distribuição unilateral":"Movimentos em um único bordo",
            "Retorno a zero ausente":"Referência inicial sem reconferência",
            "Peso possivelmente insuficiente":"Momento transversal pequeno",
            "Deflexão insuficiente":"Fio curto ou momento pequeno",
            "Critério ausente":"Falta limite de projeto",
            "Ângulo excedido":"Momento excessivo ou GM pequeno",
            "Pêndulos divergentes":"Erro de escala, zero ou leitura",
        }
        checagens={
            "Incompleto":"Contar leituras de equilíbrio e movimentos distintos",
            "Distribuição unilateral":"Conferir sinais das coordenadas Y",
            "Retorno a zero ausente":"Identificar medições na posição original",
            "Peso possivelmente insuficiente":"Conferir massa, curso e GM de planejamento",
            "Deflexão insuficiente":"Comparar deflexão máxima e divisão da régua",
            "Critério ausente":"Consultar o critério de projeto",
            "Ângulo excedido":"Revisar o limite angular e o momento",
            "Pêndulos divergentes":"Comparar as tangentes por instrumento",
        }
        registros.append({"Erro identificado":titulo,"Possível causa":causas.get(titulo,"Perturbação configurada no cenário virtual"),
                          "Consequência ou evidência":efeito,"Verificação":checagens.get(titulo,"Conferir o cenário salvo na leitura"),
                          "Procedimento":correcao,"Decisão":decisao})
    if not registros and leituras:
        registros.append({"Erro identificado":"Nenhum nos critérios verificados","Possível causa":"—",
                          "Consequência ou evidência":"Leituras compatíveis com os limites informados",
                          "Verificação":"Conferir a linearidade, os resíduos e a condição ensaiada",
                          "Procedimento":"Manter o registro das verificações","Decisão":"ACEITAR para análise acadêmica"})
    return registros

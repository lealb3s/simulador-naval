"""Ajuste y=tanφ=a+b M, GM observado=1/(Δ b).

GM observado inclui efeito da superfície livre; KG sólido=KM-GM-FSC.
Este KG não representa casco leve sem levantamento de pesos a remover.
"""
import numpy as np
from scipy.stats import linregress
from .validacao import numero


def processar(leituras, deslocamento_kg, km_m=None, fsm_kgm=None):
    deslocamento_kg=numero(deslocamento_kg,"deslocamento",positivo=True)
    validas=[r for r in leituras if r.get("momento_kgm") is not None and r.get("tangente") is not None and r.get("estavel",False)]
    if len(validas)<3:
        raise ValueError("Necessárias pelo menos 3 leituras marcadas em equilíbrio para regressão (8 condições para protocolo completo)")
    x=np.asarray([r["momento_kgm"] for r in validas],dtype=float)
    y=np.asarray([r["tangente"] for r in validas],dtype=float)
    if len(np.unique(x))<3: raise ValueError("Necessários pelo menos 3 momentos distintos")
    if not np.isfinite(x).all() or not np.isfinite(y).all(): raise ValueError("Dados não finitos")
    from .criterios import TETO_MODELO_GRAUS
    if np.any(np.abs(np.rad2deg(np.arctan(y))) > TETO_MODELO_GRAUS + 1e-9):
        raise ValueError("Leitura fora do domínio de 4° do modelo. Revise a seleção das leituras em equilíbrio.")
    if fsm_kgm is not None:
        fsm_kgm = numero(fsm_kgm,"FSM",nao_negativo=True)
    fit=linregress(x,y)
    if fit.slope <=0: raise ValueError("Inclinação da regressão não positiva: verifique sinais, instrumentos e dados")
    previsto=fit.intercept + fit.slope*x
    residuos=y-previsto
    gm=1/(deslocamento_kg*fit.slope)
    fsc=fsm_kgm/deslocamento_kg if fsm_kgm is not None else None
    kg=km_m-gm-fsc if km_m is not None and fsc is not None else None
    return {"n":len(validas),"a":float(fit.intercept),"b":float(fit.slope),"r2":float(fit.rvalue**2),
            "u_gm_ajuste_m":float(gm*fit.stderr/fit.slope),
            "dispersao_tangente":float(np.sqrt(np.sum(residuos**2)/(len(x)-2))),
            "stderr_b":float(fit.stderr),"residuos":residuos.tolist(),"x":x.tolist(),"y":y.tolist(),
            "y_ajuste":previsto.tolist(),"gm_observado_m":gm,"fsc_m":fsc,"kg_solido_m":kg,
            "avaliacao":"Sequência com >=8 leituras" if len(validas)>=8 else "PRELIMINAR: menos de 8 leituras"}


def sensibilidade(massa_kg, distancia_m, deslocamento_kg, comprimento_m, deflexao_m,
                    erros):
    """GMapprox=(m d L)/(Δ x) para uma leitura, e propagação diferencial de 1ª ordem.

    Entrada erros absolutos e mutuamente independentes; σrel quadrático.
    """
    vals=[numero(v,n,positivo=True) for n,v in zip(("massa","distancia","deslocamento","comprimento","deflexao"),
                                                    (massa_kg,distancia_m,deslocamento_kg,comprimento_m,abs(deflexao_m)))]
    gm=vals[0]*vals[1]*vals[3]/(vals[2]*vals[4])
    nomes=("massa_kg","distancia_m","deslocamento_kg","comprimento_m","deflexao_m")
    comps={k:numero(erros.get(k,0),f"σ{k}",nao_negativo=True)/v for k,v in zip(nomes,vals)}
    rel=float(np.sqrt(sum(x*x for x in comps.values())))
    return {"gm_m":gm,"incerteza_padrao_m":gm*rel,"incerteza_relativa":rel,"contribuicoes_relativas":comps,
            "hipotese":"linearização 1ª ordem; erros independentes; sem covariâncias"}

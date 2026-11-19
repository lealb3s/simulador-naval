"""Planejamento com pesos já embarcados na condição analisada."""
import math

import pandas as pd
import streamlit as st

from modules.carregamento import calcular
from modules.estabilidade import avaliar
from modules.hidrostatica import consultar
from modules.movimentacao_pesos import comparar
from utils.dados import numero_digitado

s = st.session_state
st.title("Planejamento de pesos")
st.write("Compare três maneiras de movimentar pesos que já estão a bordo. A massa deslocada e a altura dos pesos permanecem constantes em cada alternativa.")
delta = gm = None
try:
    cond = calcular(s.barco, s.cargas)
    delta = cond["deslocamento_kg"]
    hidro = consultar(s.barco, delta)
    gm = avaliar(s.barco, cond, hidro)["gm_efetivo_m"]
    if gm is None or gm <= 0:
        raise ValueError("Informe KM, KG e superfície livre para obter GM efetivo positivo.")
    st.caption(f"Condição de planejamento · Δ = {delta:g} kg · GM efetivo = {gm:.4f} m")
except ValueError as exc:
    st.info(str(exc))

with st.expander("Dimensionar para um ângulo desejado"):
    a,b=st.columns(2)
    alvo=a.number_input("Módulo da inclinação desejada (°)",min_value=.001,max_value=4.,value=None,format="%.3f")
    percurso=b.number_input("Curso disponível por peso (m)",min_value=.001,value=None,format="%.3f")
    if gm and gm>0 and delta and alvo is not None and percurso is not None:
        momento=delta*gm*math.tan(math.radians(alvo))
        st.write(f"Para atingir {alvo:g}°, o momento requerido é **{momento:.3f} kg·m**. Percorrendo {percurso:g} m, a massa total a mover é **{momento/percurso:.3f} kg**.")

limites=s.get("limites_planejamento",{})
campos=["massa_kg","quantidade","y_inicial_m","distancia_m","pendulo_m"]
base=s.configuracoes or [{} for _ in range(3)]
with st.form("configuracoes_pesos"):
    st.subheader("Limites da operação")
    a,b,c,d=st.columns(4)
    dados_lim={
        "lim_ang":a.text_input("Limite angular (°)",limites.get("lim_ang","")),
        "max_p":b.text_input("Altura livre do fio (m)",limites.get("max_p","")),
        "res_p":c.text_input("Divisão da régua (m)",limites.get("res_p","")),
        "lim_massa":d.text_input("Limite por peso (kg)",limites.get("lim_massa","")),
    }
    largura=s.barco.get("B_m")
    a,b=st.columns(2)
    y_min=a.number_input("Limite inferior do centro do peso · Y (m)",value=limites.get("y_min", -largura/2 if largura else None))
    y_max=b.number_input("Limite superior do centro do peso · Y (m)",value=limites.get("y_max", largura/2 if largura else None))
    st.caption("Ajuste o intervalo livre considerando largura dos pesos, obstáculos e folgas. A boca apenas delimita o envelope exterior.")
    st.subheader("Alternativas de prova")
    st.write("Y final = Y inicial + curso. Um curso negativo move o peso para bombordo. Quantidade indica quantos pesos iguais fazem o mesmo percurso.")
    nomes=["Massa por peso (kg)","Quantidade","Y inicial (m)","Curso assinado (m)","Pêndulo (m)"]
    df=st.data_editor(pd.DataFrame(base,columns=campos,dtype=float),num_rows="dynamic",hide_index=True,
                      column_config=dict(zip(campos,nomes)),width="stretch")
    if st.form_submit_button("Comparar configurações",type="primary"):
        try:
            configs=df.to_dict("records")
            if len(configs)<3 or df.isna().any().any():
                raise ValueError("Preencha pelo menos três alternativas completas.")
            lim={k:numero_digitado(v) if v.strip() else None for k,v in dados_lim.items()}
            if any(v is not None and v<=0 for v in lim.values()):
                raise ValueError("Os limites de operação e a divisão da régua precisam ser positivos.")
            if y_min is not None and y_max is not None and y_min>=y_max:
                raise ValueError("O limite inferior de Y deve ser menor que o superior.")
            for cfg in configs:
                if not cfg["quantidade"].is_integer() or cfg["quantidade"]<1:
                    raise ValueError("A quantidade de pesos deve ser um inteiro positivo.")
                if cfg["pendulo_m"]<=0 or cfg["massa_kg"]<=0 or cfg["distancia_m"]==0:
                    raise ValueError("Informe massa e pêndulo positivos e curso diferente de zero.")
                cfg["quantidade"]=int(cfg["quantidade"])
            tabela=comparar([{**c,"distancia_m":abs(c["distancia_m"])} for c in configs],delta,gm,largura,
                            lim["max_p"],lim["lim_ang"],lim["res_p"])
            for cfg,r in zip(configs,tabela):
                inicio=cfg["y_inicial_m"]
                fim=inicio+cfg["distancia_m"]
                sinal=math.copysign(1,cfg["distancia_m"])
                r["Y inicial (m)"],r["Y final (m)"]=inicio,fim
                r["Momento (kg m)"]*=sinal
                phi=r["Inclinação prevista (°)"]
                problemas=[r["Pendências / violações"]] if r["Pendências / violações"] else []
                if lim["lim_massa"] is None or cfg["massa_kg"]>lim["lim_massa"]:
                    problemas.append("Limite individual ausente ou ultrapassado")
                if y_min is None or y_max is None or not all(y_min<=v<=y_max for v in (inicio,fim)):
                    problemas.append("Confirmar o intervalo de curso livre")
                if largura and max(abs(inicio),abs(fim))>largura/2:
                    problemas.append("Posição fora da boca")
                if delta and r["Massa total (kg)"]>delta:
                    problemas.append("Massa móvel superior ao deslocamento")
                if phi is not None and phi>4:
                    problemas.append("Fora do domínio de pequenos ângulos adotado")
                    phi=None
                r["Inclinação prevista (°)"]=None if phi is None else sinal*phi
                r["Tangente prevista"]=None if phi is None else sinal*math.tan(math.radians(phi))
                r["Pendências / violações"]=" · ".join(problemas)
                r["Viabilidade"]="Pendente" if problemas else "Atende aos limites declarados"
            s.configuracoes=configs
            s.tabela_planejamento=tabela
            s.limites_planejamento={**dados_lim,"y_min":y_min,"y_max":y_max}
        except ValueError as exc:
            s.pop("tabela_planejamento",None)
            st.error(str(exc))

if s.get("tabela_planejamento"):
    tabela=s.tabela_planejamento
    st.dataframe(tabela,hide_index=True)
    viaveis=[r for r in tabela if not r["Pendências / violações"]]
    if viaveis:
        rec=max(viaveis,key=lambda r:(abs(r["Inclinação prevista (°)"])/r["Resolução angular (°)"],-r["Quantidade"]))
        st.success(f"Configuração {rec['Configuração']} sugerida. Entre as opções dentro dos limites, oferece a maior razão entre inclinação e resolução angular. Em empate, prioriza menos pesos.")
    else:
        st.info("Confira as pendências de cada alternativa antes de escolher.")
    st.caption("A comparação pressupõe os pesos a bordo. Resistência local do convés, acesso, amarras e trajeto livre precisam de verificação própria.")

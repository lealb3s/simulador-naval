from utils.navegacao import atalho
from utils.dados import numero_digitado
import pandas as pd
import streamlit as st
from modules.pendulos import comparar,deflexao,angulo
from utils.estado import inicializar
from visualization.pendulos import desenhar

def render():
    inicializar();st.title("Pêndulos")
    if st.session_state.prova_em_andamento:
        st.info("A condição está congelada durante a prova. Encerre o ensaio para voltar a editar.")
        atalho("ensaio", "Retomar o ensaio ativo")
        return
    st.write("Mínimo de dois instrumentos, com posições/leituras independentes. As expressões tan(θ)=x/L pressupõem equilíbrio estático do fio.")
    q=st.number_input("Quantidade de pêndulos",min_value=2,max_value=6,value=max(2,len(st.session_state.pendulos)))
    cfg = st.session_state.get("config_pendulos", {})
    with st.form("pendulo_form"):
        inputs=[]
        for i in range(q):
            known=st.session_state.pendulos[i]["comprimento_m"] if i<len(st.session_state.pendulos) else None
            inputs.append(st.text_input(f"Pêndulo {i+1} — comprimento L (m)",value="" if known is None else str(known),key=f"plen_{i}"))
        res=st.text_input("Resolução linear da escala (m)",value=str(cfg["res"]) if cfg.get("res") is not None else "", key="pend_res")
        ang=st.text_input("Ângulo previsto para comparação (graus; opcional)",value=str(cfg["ang"]) if cfg.get("ang") is not None else "", key="pend_ang")
        max_alt=st.text_input("Altura disponível (m; opcional)",value=str(cfg["alt"]) if cfg.get("alt") is not None else "", key="pend_alt")
        if st.form_submit_button("Validar e salvar instrumentos"):
            try:
                pend=[{"id":f"P{i+1}","comprimento_m":numero_digitado(v)} for i,v in enumerate(inputs)]
                if any(p["comprimento_m"]<=0 for p in pend):raise ValueError("Todos os comprimentos devem ser >0")
                if max_alt.strip() and any(p["comprimento_m"]>numero_digitado(max_alt) for p in pend):raise ValueError("Comprimento maior que altura disponível")
                resolucao = numero_digitado(res) if res.strip() else None
                previsto = numero_digitado(ang) if ang.strip() else None
                if resolucao is not None and resolucao <= 0:
                    raise ValueError("A resolução deve ser positiva")
                if previsto is not None and abs(previsto)>4:
                    raise ValueError("Compare ângulos dentro da faixa didática de ±4°.")
                st.session_state.config_pendulos = dict(res=resolucao, ang=previsto, alt=numero_digitado(max_alt) if max_alt.strip() else None)
                st.session_state.pendulos=pend
                st.success("Pêndulos registrados")
            except Exception as ex:st.error(str(ex))
    pend=st.session_state.pendulos
    if all(p["comprimento_m"] for p in pend):
        cfg = st.session_state.get("config_pendulos", {})
        if cfg.get("res") is not None:
            try:
                tab=comparar([p["comprimento_m"] for p in pend],cfg["res"], cfg.get("ang"))
                st.dataframe(pd.DataFrame(tab),width="stretch",hide_index=True)
            except ValueError as e:st.error(str(e))
        st.plotly_chart(desenhar(pend,{p["id"]:deflexao(p["comprimento_m"],cfg.get("ang") or 0) for p in pend}),width="stretch")
    with st.expander("Dimensionar o comprimento para uma deflexão desejada"):
        from math import tan, radians
        a,b=st.columns(2)
        phi=a.number_input("Banda de projeto (°)",min_value=.001,max_value=4.,value=None,format="%.3f")
        alvo=b.number_input("Deflexão mínima desejada (m)",min_value=.0001,value=None,format="%.4f")
        if phi is not None and alvo is not None:
            comp=alvo/tan(radians(phi))
            st.metric("Comprimento vertical mínimo entre suspensão e régua",f"{comp:.4f} m")
            if cfg.get("alt") is not None and comp>cfg["alt"]:
                st.info("O comprimento requerido excede a altura disponível. Reveja o sinal desejado ou a instalação.")
    st.subheader("Comparar três comprimentos candidatos")
    with st.form("comp_pend"):
        cs=st.columns(3)
        compr=[cs[i].text_input(f"Candidato {i+1} (m)",key=f"cpen{i}") for i in range(3)]
        resolu=st.text_input("Resolução de régua para candidatos (m)",key="cpend_res")
        a=st.text_input("Inclinação para avaliar deflexão (°)",key="cpend_angle")
        if st.form_submit_button("Comparar três comprimentos"):
            try:
                if any(not v for v in compr) or not resolu or not a:raise ValueError("Preencha todos os campos")
                if abs(numero_digitado(a))>4:
                    raise ValueError("Compare ângulos dentro da faixa didática de ±4°.")
                result=comparar([numero_digitado(x) for x in compr],numero_digitado(resolu),numero_digitado(a))
                for linha,L in zip(result,compr):
                    linha["Instalação"] = ("Altura não informada" if cfg.get("alt") is None else
                                          "Cabe na altura informada" if numero_digitado(L)<=cfg["alt"] else "Excede a altura")
                st.dataframe(pd.DataFrame(result),width="stretch",hide_index=True)
                st.info("Quanto maior L, menor resolução angular geométrica para a mesma régua; mas maior espaço e potencial de interferência dinâmica. Não é sinônimo de precisão total do ensaio.")
            except ValueError as ex:st.error(str(ex))


render()

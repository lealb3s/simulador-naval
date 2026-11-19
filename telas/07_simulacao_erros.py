from utils.dados import numero_digitado
import copy
import pandas as pd
import streamlit as st
from modules.erros_experimentais import diagnostico_detalhado
from utils.estado import inicializar

inicializar();st.title("Condições do ensaio")
st.write("Parâmetros iguais a zero significam nenhum erro; a magnitude é definida pelo usuário. O erro é aplicado às **próximas** leituras virtuais, sem alterar dados anteriores.")
with st.form("erros_prova"):
    old=st.session_state.erros
    st.subheader("Limite para registrar leituras")
    st.caption("Informe o limite adotado no projeto em graus. Os parâmetros de erro abaixo são opcionais.")
    ang=st.text_input("Limite angular do ensaio (°)",value="" if old.get("limite_angulo_graus") is None else str(old["limite_angulo_graus"]))
    st.markdown("**Erros sistemáticos e aleatórios**")
    col1,col2=st.columns(2)
    with col1:
        massa=st.number_input("Viés sistemático da massa medida (%)",value=numero_digitado(old.get("vies_massa_pct",0)),format="%.5f")
        dist=st.number_input("Viés sistemático de distância medida (%)",value=numero_digitado(old.get("vies_dist_pct",0)),format="%.5f")
        referencia=st.number_input("Erro sistemático de zero do pêndulo (m)",value=numero_digitado(old.get("vies_referencia_m",0)),format="%.6f")
    with col2:
        sigma=st.number_input("Desvio-padrão da leitura (m) — erro aleatório normal",min_value=0.,value=numero_digitado(old.get("desvio_leitura_m",0)),format="%.6f")
        vento=st.number_input("Momento EXTERNO constante de vento/interferência (N·m; sinal)",value=numero_digitado(old.get("momento_vento_Nm",0)),format="%.5f")
        sigma_vento=st.number_input("Vento variável entre movimentações · desvio-padrão (N·m)",min_value=0.,value=float(old.get("sigma_vento_Nm",0)))
        externo=st.number_input("Interferência externa assinada (N·m)",value=float(old.get("interferencia_Nm",0)))
        erro_l=st.number_input("Viés do comprimento informado dos fios (%)",min_value=-99.99,value=float(old.get("vies_comprimento_pct",0)))
    fsm_extra=st.number_input("Momento adicional de superfície livre para o cenário (kg·m)",min_value=0.,value=float(old.get("fsm_extra_kgm",0)),disabled=st.session_state.prova_em_andamento)
    st.caption("O cenário soma este momento ao FSM dos tanques. O total fica fixo durante a prova. Use zero para desativar cada efeito.")
    tol=st.text_input("Desacordo máximo permitido entre pêndulos (graus)",value="" if old.get("tolerancia_pendulos_graus") is None else str(old["tolerancia_pendulos_graus"]))
    a1,a2=st.columns(2)
    ang_min=a1.text_input("Inclinação mínima desejada por bordo (°)",value="" if old.get("minimo_angulo_graus") is None else str(old["minimo_angulo_graus"]))
    min_def=a2.text_input("Deflexão mínima de pêndulo desejada (m)",value="" if old.get("minima_deflexao_m") is None else str(old["minima_deflexao_m"]))
    if st.form_submit_button("Salvar condições do ensaio"):
        try:
            val={"vies_massa_pct":massa,"vies_dist_pct":dist,"vies_referencia_m":referencia,"desvio_leitura_m":sigma,"momento_vento_Nm":vento,
                 "limite_angulo_graus":numero_digitado(ang) if ang.strip() else None,"tolerancia_pendulos_graus":numero_digitado(tol) if tol.strip() else None,
                 "minimo_angulo_graus":numero_digitado(ang_min) if ang_min.strip() else None,"minima_deflexao_m":numero_digitado(min_def) if min_def.strip() else None}
            val.update(sigma_vento_Nm=sigma_vento,interferencia_Nm=externo,vies_comprimento_pct=erro_l,fsm_extra_kgm=fsm_extra)
            if massa <= -100 or dist <= -100:
                raise ValueError("O viés deve preservar massa e módulo da distância positivos.")
            if val["limite_angulo_graus"] is not None and val["limite_angulo_graus"] > 4:
                raise ValueError("Este modelo didático de pequenos ângulos admite limite até 4°.")
            if val["limite_angulo_graus"] is not None and val["limite_angulo_graus"]<=0:raise ValueError("Limite angular deve ser positivo")
            if val["tolerancia_pendulos_graus"] is not None and val["tolerancia_pendulos_graus"]<=0:raise ValueError("Tolerância deve ser positiva")
            for k in ("minimo_angulo_graus","minima_deflexao_m"):
                if val[k] is not None and val[k]<=0:raise ValueError(f"{k} precisa ser positivo")
            if val["minimo_angulo_graus"] is not None and val["limite_angulo_graus"] is not None and val["minimo_angulo_graus"]>val["limite_angulo_graus"]:
                raise ValueError("Inclinação mínima não pode exceder o máximo")
            st.session_state.erros=val;st.success("Cenário definido e válido para leituras futuras")
        except Exception as ex:st.error(str(ex))
st.markdown("**Superfície livre:** não é uma perturbação aleatória; informe seu momento corrigido em kg·m em Embarcação. Se ausente, o GM efetivo e a prova virtual ficam bloqueados.")
st.markdown("**Pesos insuficientes/excessivos:** dependem de limites declarados para ângulo e resolução; o simulador não assume limiares genéricos.")
if st.session_state.leituras:
    avisos=diagnostico_detalhado(st.session_state.erros,st.session_state.leituras,st.session_state.erros.get("limite_angulo_graus"))
    if avisos:
        st.subheader("Diagnósticos")
        st.dataframe(pd.DataFrame(avisos),width="stretch")
    else:st.success("Nenhum alerta detectado segundo os dados e limites definidos — não implica aprovação regulamentar")
else:st.info("O diagnóstico dos resultados aparecerá depois das leituras no Ensaio virtual ou em Processamento.")
st.warning("Vento informado como momento externo conhecido (N·m), não estimado de área e coeficiente aerodinâmico. Correntes, ondas, amarras, deslocamento de líquidos e falhas de instrumentos não são modelados automaticamente.")

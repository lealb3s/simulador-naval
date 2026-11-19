from utils.dados import numero_digitado
from math import atan,degrees
import pandas as pd
import numpy as np
import streamlit as st
from modules.regressao import processar,sensibilidade
from modules.carregamento import calcular
from modules.hidrostatica import consultar
from modules.erros_experimentais import diagnostico_detalhado
from visualization.graficos import ajuste,residuos
from utils.estado import inicializar, salvar_leituras
from utils.dados import ler,csv_bytes,tabela_para_lista
from utils.ui_importacao import fonte_tabela, arquivo_recebido,controles_tabela,mapear_campos,aplicar_mapeamento

inicializar();st.title("Processamento de GM e KG")
st.write("Regressão com intercepto: tan θ = a + b·(Σm·d), com GM observado = 1/(Δ·b). KM e momento de superfície livre referem-se à MESMA condição da prova.")
if st.session_state.prova_em_andamento:
    from utils.navegacao import atalho
    st.info("Encerre o ensaio para importar ou editar as medições. As leituras registradas já estão disponíveis para consulta.")
    atalho("ensaio", "Retomar ensaio virtual")
else:
    with st.expander("Importar ou editar medições", expanded=not st.session_state.leituras or bool(st.session_state.get("tabela_para_processamento"))):
        st.caption("CSV/XLSX/JSON: campos 'momento_kgm', 'tangente', 'estavel' (bool), 'fonte'. Cada linha deve representar leitura com deslocamento constante.")
        up=fonte_tabela("Medições","processamento","up_leituras")
        up = arquivo_recebido(up, "processamento")
        if up:
            try:
                import hashlib
                uid=hashlib.sha1(up.getvalue()).hexdigest()[:10]
                aba,head,decimal_virgula,sugerido=controles_tabela(up,'processamento', ('leituras',))
                rows=ler(up,'leituras',aba=aba,cabecalho_linha=head,decimal_virgula=decimal_virgula)
                if not rows:raise ValueError('Nenhuma leitura na aba selecionada.')
                st.dataframe(pd.DataFrame(rows).drop(columns=['__linha_origem__'],errors='ignore').head(8),
                             width="stretch",hide_index=True)
                if not up.name.lower().endswith('.json'):
                    colmap=mapear_campos(rows,'leituras',
                         ['momento_kgm','tangente','estavel','fonte'],
                         ['momento_kgm','tangente'],f'leituras_map_{uid}_{aba}_{head}')
                if st.button("Validar e importar medições (substituir)"):
                    if up.name.lower().endswith('.json'):
                        maprows=rows
                    else:
                        from utils.importacao import verificar_unidade_declarada, unidade_declarada
                        momento_declarado=unidade_declarada(colmap["momento_kgm"])
                        if momento_declarado not in (None,"kgm","kg.m","kg·m"):
                            raise ValueError("Converta o momento para kg·m antes de importar.")
                        maprows=aplicar_mapeamento(rows,colmap,['momento_kgm','tangente'])
                    clean=tabela_para_lista(maprows,['momento_kgm','tangente'],decimal_virgula=decimal_virgula)
                    # Metadados usam as linhas de origem para não perder a ordem.
                    if len(clean)!=len(maprows):
                        raise ValueError('Existem linhas com apenas metadados. Remova ou corrija antes de importar.')
                    new=[]
                    for i,(r,c) in enumerate(zip(maprows,clean),1):
                        if c['momento_kgm'] is None or c['tangente'] is None:
                            raise ValueError(f'Linha {r.get("__linha_origem__",i)}: momento e tangente são obrigatórios.')
                        flag=r.get('estavel')
                        if flag is None:
                            estavel=False
                        else:
                            estavel=str(flag).strip().lower() in ('true','1','sim','yes','verdadeiro')
                        # Na ausência de medição de estabilidade, não declarar leitura estável.
                        new.append({'numero':i,'momento_kgm':c['momento_kgm'],
                                    'tangente':c['tangente'],'estavel':estavel,
                                    'fonte':r.get('fonte') or 'medicao_importada',
                                    'angulo_graus':degrees(atan(c['tangente']))})
                    st.session_state.pop("condicao_ensaio", None)
                    salvar_leituras(new)
                    st.success(f'{len(new)} medições importadas. Sem campo estavel, são marcadas como não estabilizadas.')
            except Exception as ex:st.error('Falha ao importar medições: '+str(ex))
        edit=pd.DataFrame([{k:v for k,v in r.items() if k in ("momento_kgm","tangente","estavel","fonte")} for r in st.session_state.leituras],columns=["momento_kgm","tangente","estavel","fonte"])
        edit = edit.astype({"momento_kgm":"float64", "tangente":"float64", "estavel":"boolean", "fonte":"string"})
        ed=st.data_editor(edit,num_rows="dynamic",width="stretch",key=f"edit_medicoes_{st.session_state.revisao_leituras}")
        if st.button("Salvar medições editadas"):
            try:
                new=[]
                for i,r in enumerate(ed.to_dict("records")):
                    if pd.isna(r["momento_kgm"]) or pd.isna(r["tangente"]):raise ValueError("Todos os momentos e tangentes devem estar preenchidos")
                    tt=numero_digitado(r["tangente"])
                    new.append({"numero":i+1,"momento_kgm":numero_digitado(r["momento_kgm"]),"tangente":tt,
                                "estavel":bool(r["estavel"]) if pd.notna(r["estavel"]) else False,
                                "fonte":str(r["fonte"]) if pd.notna(r["fonte"]) and r["fonte"] else "medicao_manual","angulo_graus":degrees(atan(tt))})
                if len(new)==len(st.session_state.leituras):
                    for idx,(atual,original) in enumerate(zip(new,st.session_state.leituras)):
                        if all(atual[k]==original.get(k) for k in ("momento_kgm","tangente","fonte")):
                            new[idx]={**original,"estavel":atual["estavel"]}
                        else:
                            atual["fonte"]="medicao_editada"
                else:
                    for atual in new:
                        atual["fonte"]="medicao_editada"
                if any(r["fonte"]=="medicao_editada" for r in new):
                    st.session_state.pop("condicao_ensaio",None)
                salvar_leituras(new);st.success("Leituras salvas")
            except Exception as ex:st.error(str(ex))
try:
    delta=calcular(st.session_state.barco,st.session_state.cargas)["deslocamento_kg"]
except ValueError:delta=None
condicao = st.session_state.get("condicao_ensaio") or {}
parametros = st.session_state.get("param_regressao") or condicao
delta = parametros.get("delta", delta)
try:
    km_inicial = consultar(st.session_state.barco, delta)["km_m"] if delta is not None else None
except ValueError:
    km_inicial = None
km_atual = parametros.get("km", km_inicial)
fsm_atual = parametros.get("fsm", st.session_state.barco.get("fsm_kgm"))
with st.form("param_reducao"):
    a,b,c=st.columns(3)
    despl=a.text_input("Deslocamento da condição da prova (kg)",value="" if delta is None else str(delta))
    km=b.text_input("KM dessa condição (m)",value="" if km_atual is None else str(km_atual))
    fsm=c.text_input("FSM efetivo dos tanques (kg·m; zero se inexistente comprovado)",value="" if fsm_atual is None else str(fsm_atual))
    if st.form_submit_button("Calcular regressão"):
        try:
            d=numero_digitado(despl)
            if not d>0:raise ValueError("Deslocamento deve ser positivo")
            k=numero_digitado(km) if km.strip() else None
            f=numero_digitado(fsm) if fsm.strip() else None
            if f is not None and f<0:raise ValueError("FSM não pode ser negativo")
            r=processar(st.session_state.leituras,d,k,f)
            st.session_state.ultima_regressao=r
            st.session_state.param_regressao={"delta":d,"km":k,"fsm":f}
        except (ValueError, TypeError) as ex:
            from utils.estado import limpar_resultados
            limpar_resultados()
            st.error(str(ex))
if st.session_state.get("ultima_regressao"):
    r=st.session_state.ultima_regressao
    st.caption("Resultados calculados com as leituras em equilíbrio e os parâmetros do formulário.")
    a,b,c,d=st.columns(4)
    a.metric("GM observado (m)",f"{r['gm_observado_m']:.6f}")
    b.metric("KG sólido (m)",f"{r['kg_solido_m']:.6f}" if r["kg_solido_m"] is not None else "Pendente KM/FSM")
    c.metric("R²",f"{r['r2']:.6f}")
    d.metric("n",r["n"])
    st.write(f"**Equação:** tan θ = ({r['a']:.8g}) + ({r['b']:.8g}) × M, onde M em kg·m e b em (kg·m)⁻¹.")
    st.caption(f"Desvio-padrão do estimador da inclinação da reta: {r['stderr_b']:.3g} (kg·m)⁻¹. {r['avaliacao']}. Não é incerteza expandida de GM.")
    st.write(f"Incerteza padrão de GM atribuível ao ajuste: **{r['u_gm_ajuste_m']:.5g} m**. Dispersão residual da tangente: {r['dispersao_tangente']:.5g}.")
    st.caption("Estimativa condicionada a Δ e momentos conhecidos, com resíduos independentes de variância constante. Vieses de calibração podem persistir mesmo com R² próximo de 1.")
    if condicao.get("gm_ref") is not None:
        parametros = st.session_state.param_regressao
        if all(parametros[k] == condicao[k] for k in ("delta","km","fsm")):
            tabela = [{"Grandeza": "GM efetivo", "Referência (m)":condicao["gm_ref"],"Experimental (m)":r["gm_observado_m"]},
                      {"Grandeza":"KG sólido","Referência (m)":condicao["kg_ref"],"Experimental (m)":r["kg_solido_m"]}]
            for item in tabela:
                item["Diferença (m)"] = item["Experimental (m)"] - item["Referência (m)"]
            st.dataframe(pd.DataFrame(tabela),hide_index=True)
        else:
            st.info("Os parâmetros do processamento diferem da condição virtual congelada.")
    st.plotly_chart(ajuste(r),width="stretch")
    st.plotly_chart(residuos(r),width="stretch")
    st.warning("O KG obtido corresponde à condição ENSAIADA, não ao KG do navio leve. Remoções/adições para condição leve exigem levantamento de pesos e momentos separado.")
if st.session_state.leituras:
    st.subheader("Diagnóstico dos dados")
    warns=diagnostico_detalhado(st.session_state.erros,st.session_state.leituras,st.session_state.erros.get("limite_angulo_graus"))
    if warns:st.dataframe(pd.DataFrame(warns),width="stretch")
    else:st.info("Sem alertas automáticos dentro dos critérios fornecidos.")
    st.download_button("Exportar medições CSV",csv_bytes(st.session_state.leituras),file_name="leituras.csv")
with st.expander("Sensibilidade por uma leitura isolada"):
    st.write("Usa GM=m·d·L/(Δ·x), com propagação de erros pequenos, independentes. Não usar x=0, não extrapolar para erros grandes.")
    keys=[("Massa inclinante (kg)","massa"),("Distância medida (m)","dist"),("Deslocamento (kg)","delta"),("Comprimento fio (m)","L"),("Deflexão (m)","x")]
    vals={}
    cols=st.columns(2)
    for i,(label,k) in enumerate(keys):
        vals[k]=cols[i%2].text_input(label,key="sens_v_"+k)
    inc={}
    for i,(label,k) in enumerate(keys):
        inc[k]=cols[i%2].text_input("Incerteza padrão absoluta — "+label,key="sens_i_"+k)
    if st.button("Calcular sensibilidade"):
        try:
            if any(not vals[k] or not inc[k] for _,k in keys):raise ValueError("Preencha medidas e incertezas (0 permitido para incerteza)")
            params={"massa_kg":numero_digitado(inc["massa"]),"distancia_m":numero_digitado(inc["dist"]),"deslocamento_kg":numero_digitado(inc["delta"]),
                    "comprimento_m":numero_digitado(inc["L"]),"deflexao_m":numero_digitado(inc["x"])}
            r=sensibilidade(*(numero_digitado(vals[k]) for _,k in keys),params)
            st.session_state.estudo_sensibilidade={"medidas":vals.copy(),"incertezas":params,"resultado":r}
        except ValueError as ex:
            st.session_state.pop("estudo_sensibilidade",None)
            st.error(str(ex))
    if st.session_state.get("estudo_sensibilidade"):
        estudo=st.session_state.estudo_sensibilidade
        st.write(f"GM da leitura: {estudo['resultado']['gm_m']:.5g} m · Incerteza padrão combinada: {estudo['resultado']['incerteza_padrao_m']:.4g} m")
        st.dataframe([{"Entrada":k,"Incerteza relativa (%)":100*v} for k,v in estudo["resultado"]["contribuicoes_relativas"].items()], hide_index=True)

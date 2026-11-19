from utils.navegacao import selecionar_carga
from utils.dados import numero_digitado
import copy
from datetime import datetime, timezone
from math import atan, degrees, radians, tan
import numpy as np
import pandas as pd
import streamlit as st
from modules.carregamento import calcular
from modules.hidrostatica import consultar
from modules.estabilidade import avaliar
from modules.prova_inclinacao import equilibrio_angulo,serie_transitoria,estabilizado,G0
from modules.erros_experimentais import perturbar, momento_externo
from utils.estado import inicializar, salvar_leituras
from utils.navegacao import atalho
from utils.dados import csv_bytes
from visualization.inclinacao import secao
from visualization.pendulos import desenhar

def render():
    inicializar();st.title("Ensaio virtual")
    st.write("As cargas inclinantes devem ser cadastradas em Carregamento. Neste modo só se movimenta Y; massa, X e Z permanecem inalterados. O histórico de medições permanece separado do carregamento original.")
    try:
        b=st.session_state.barco;cargas=st.session_state.cargas
        destino = "embarcacao"
        if not cargas:
            destino = "cargas"
            raise ValueError("Cadastre pelo menos um peso para movimentar.")
        cond=calcular(b,cargas)
        h=consultar(b,cond["deslocamento_kg"])
        fsm_extra = st.session_state.erros.get("fsm_extra_kgm", 0)
        fsm_total = None if b.get("fsm_kgm") is None else b["fsm_kgm"] + fsm_extra
        e=avaliar({**b,"fsm_kgm":fsm_total},cond,h)
        if e["gm_efetivo_m"] is None or e["gm_efetivo_m"]<=0:raise ValueError("Exige KM, KG, superfície livre explícita e GM efetivo > 0")
        if cond["tcg_m"] is None or not np.isclose(cond["tcg_m"],0,rtol=0,atol=1e-9):
            destino = "cargas" if cond["tcg_m"] is not None else "embarcacao"
            raise ValueError("Para este modelo virtual, a condição inicial deve ter TCG=0. Corrija adernamento inicial ou use dados reais em Processamento")
        destino = "pendulos"
        pend=st.session_state.pendulos
        if len(pend)<2 or any(p["comprimento_m"] is None or p["comprimento_m"]<=0 for p in pend):raise ValueError("Configure pelo menos dois pêndulos em Pêndulos")
        destino = "condicoes"
        if st.session_state.erros.get("limite_angulo_graus") is None and not st.session_state.prova_em_andamento:
            raise ValueError("Defina e salve o limite angular antes de iniciar a prova.")
        m=cond["deslocamento_kg"];gm=e["gm_efetivo_m"]
    except ValueError as ex:
        st.info(str(ex))
        nomes = {"embarcacao":"Embarcação","cargas":"Carregamento","pendulos":"Pêndulos","condicoes":"Condições do ensaio"}
        atalho(destino, f"Abrir {nomes[destino]}")
        return

    if not st.session_state.prova_em_andamento:
        st.info(f"Condição inicial: Δ = {m:.3f} kg, GM efetivo = {gm:.5f} m. O instrumento registra deflexão relativa ao zero inicial.")
        autorizado = True
        if st.session_state.leituras or st.session_state.movimentos:
            autorizado = st.checkbox("Iniciar uma nova prova e substituir os movimentos e leituras da sessão")
            atalho("processamento", "Processar as leituras existentes")
        if st.button("Iniciar prova e congelar condição de carregamento",type="primary",disabled=not autorizado):
            st.session_state.pesos_inicio=copy.deepcopy(cargas)
            st.session_state.prova_y={c["id"]:c["y_m"] for c in cargas}
            st.session_state.condicao_ensaio = {
                "barco": copy.deepcopy(b), "cargas": copy.deepcopy(cargas), "pendulos": copy.deepcopy(pend),
                "delta": m, "km": h["km_m"], "fsm": fsm_total, "gm_ref":gm, "kg_ref":cond["kg_m"],
            }
            salvar_leituras([]);st.session_state.movimentos=[];st.session_state.prova_em_andamento=True
            st.session_state.serie_dinamica=[]
            st.session_state.dinamica={"phi_rad":0,"omega_rad_s":0,"tempo_s":0}
            st.rerun()
        return

    ref=st.session_state.pesos_inicio
    curr=st.session_state.prova_y
    momento=sum(c["massa_kg"]*(curr[c["id"]]-c["y_m"]) for c in ref)
    vento=momento_externo(st.session_state.erros,len(st.session_state.movimentos))
    mom_real=momento+vento/G0
    teorico=equilibrio_angulo(mom_real,m,gm)
    if st.session_state.get("exemplo_ativo"):
        with st.expander("Roteiro do pontão · oito movimentos e nove leituras",expanded=not st.session_state.leituras):
            st.write("Registre o zero inicial. Em cada linha, escolha o peso, aplique a coordenada e registre uma leitura. Os demais pesos permanecem na posição anterior.")
            st.dataframe(pd.DataFrame({"Passo":range(1,9),"Peso":["Vante","Ré","Vante","Ré","Vante","Ré","Vante","Ré"],
                    "Y final (m)":[1.25,1.25,0,0,-1.25,-1.25,0,0]}),hide_index=True)
    col1,col2,col3=st.columns(3)
    col1.metric("Momento peso m·d (kg·m)",f"{momento:.6g}")
    col2.metric("Equilíbrio previsto (°)",f"{teorico:.5f}" if abs(teorico)<=4 else "Fora do domínio")
    col3.metric("Leituras registradas",len(st.session_state.leituras))

    with st.expander("Modelo transitório opcional — somente com parâmetros fornecidos"):
        ativo=st.checkbox("Habilitar modelo dinâmico linear de rolamento",value=st.session_state.dinamica_config is not None)
        if ativo:
            with st.form("dinamica_configuracao"):
                a=st.text_input("Inércia efetiva Ixx (kg·m²), incluindo efeitos relevantes",value=str((st.session_state.dinamica_config or {}).get("I", "")))
                c=st.text_input("Amortecimento linear c (N·m·s/rad)",value=str((st.session_state.dinamica_config or {}).get("c", "")))
                t1=st.text_input("Tolerância angular de estabilização (°)",value=str((st.session_state.dinamica_config or {}).get("tol_angulo", "")))
                t2=st.text_input("Tolerância de velocidade (°/s)",value=str((st.session_state.dinamica_config or {}).get("tol_vel", "")))
                if st.form_submit_button("Aplicar parâmetros dinâmicos"):
                    try:
                        conf={"I":numero_digitado(a),"c":numero_digitado(c),"tol_angulo":numero_digitado(t1),"tol_vel":numero_digitado(t2)}
                        if conf["I"]<=0 or conf["c"]<0 or conf["tol_angulo"]<=0 or conf["tol_vel"]<=0:raise ValueError("Parâmetros fora da faixa")
                        st.session_state.dinamica_config=conf;st.success("Modelo dinâmico ativado")
                    except Exception as ex:st.error(str(ex))
        else:st.session_state.dinamica_config=None

    st.subheader("Mover peso na transversal")
    id=selecionar_carga("Peso a movimentar", ref)
    q=next(c for c in ref if c["id"]==id)
    with st.form("form_mover"):
        y=st.number_input("Nova coordenada Y (m)",value=numero_digitado(curr[id]),format="%.6f")
        if st.form_submit_button("Movimentar o peso"):
            if b.get("B_m") is not None and abs(y)>b["B_m"]/2:
                st.error("Fora da boca nominal declarada")
            elif q.get("larg_m") is not None and b.get("B_m") is not None and abs(y)+q["larg_m"]/2>b["B_m"]/2:
                st.error("As dimensões da carga não cabem na boca declarada")
            else:
                antes=curr[id]
                st.session_state.prova_y[id]=y
                st.session_state.movimentos.append({"id_carga":id,"nome":q["nome"],"y_anterior_m":antes,"y_novo_m":y,
                    "momento_kgm":sum(c["massa_kg"]*(st.session_state.prova_y[c["id"]]-c["y_m"]) for c in ref),
                    "instante":datetime.now(timezone.utc).isoformat()})
                st.rerun()

    conf=st.session_state.dinamica_config
    if conf:
        state=st.session_state.dinamica
        dyn_eq=degrees(mom_real/(m*gm))
        col_angulo,col_velocidade=st.columns(2)
        col_angulo.metric("Ângulo dinâmico (°)",f"{degrees(state['phi_rad']):.5f}")
        col_velocidade.metric("Velocidade angular (°/s)",f"{degrees(state['omega_rad_s']):.5f}")
        dt=st.number_input("Avançar tempo de simulação (s)",min_value=0.01,value=1.,step=0.25)
        if st.button("Avançar dinâmica"):
            try:
                serie=serie_transitoria(state,mom_real,m,gm,conf,dt)
                st.session_state.serie_dinamica.extend(serie[1:] if st.session_state.serie_dinamica else serie)
                st.session_state.dinamica=serie[-1]
                st.rerun()
            except (ValueError, RuntimeError) as ex:
                st.error(str(ex))
        ok=estabilizado(state,mom_real,m,gm,conf["tol_angulo"],conf["tol_vel"])
        shown=degrees(state["phi_rad"])
        if st.session_state.get("serie_dinamica"):
            curva=pd.DataFrame(st.session_state.serie_dinamica)
            curva["Banda (°)"]=np.rad2deg(curva["phi_rad"])
            st.line_chart(curva,x="tempo_s",y="Banda (°)",x_label="Tempo simulado (s)")
        if ok:st.success("Equilíbrio atingido nas tolerâncias INFORMADAS para o modelo dinâmico")
        else:st.warning("Ainda há movimento transitório relevante: registro estabilizado bloqueado")
        st.caption("Equilíbrio dinâmico linear φ≈M/(Δ·GM) rad. A exibição do ângulo por atan é a aproximação metacêntrica estática; para ângulos grandes nenhum dos dois substitui GZ.")
    else:
        ok=not ativo
        shown=teorico
        if ativo:
            st.info("Aplique os parâmetros dinâmicos antes de registrar.")
        st.info("Modo QUASE ESTÁTICO IDEAL: não há tempo nem oscilações calculados. Uma leitura pode ser registrada como 'equilíbrio teórico', nunca como estabilização dinâmica observada.")

    st.caption(f"Momento externo aplicado neste patamar: {vento:+.4g} N·m. Boreste corresponde a Y positivo.")
    posicoes = [{"Peso":c["nome"], "Y inicial (m)":c["y_m"], "Y atual (m)":curr[c["id"]],
                 "Deslocamento transversal (m)":curr[c["id"]]-c["y_m"]} for c in ref]
    st.dataframe(pd.DataFrame(posicoes), hide_index=True)
    tcg_atual=cond["tcg_m"] + momento/m
    vis=secao({**b,"calado_m":h.get("calado_m")},shown,cond["kg_m"],h.get("kb_m"),h.get("km_m"),tcg_atual) if abs(shown)<=4 else None
    if vis:st.plotly_chart(vis,width="stretch")
    if abs(shown)<=4: st.plotly_chart(desenhar(pend,{p["id"]:p["comprimento_m"]*tan(radians(shown)) for p in pend}),width="stretch")
    st.write("**Momento inclinado:** inclua influências externas em Condições do ensaio; se o limite angular admissível for excedido, interrompa o ensaio.")
    limite=st.session_state.erros.get("limite_angulo_graus")
    limite_ok=limite is not None and max(abs(shown),abs(teorico))<=min(limite,4.)
    if limite is None:st.warning("Informe o limite angular de projeto em Condições do ensaio para liberar o registro. A IMO recomenda 1° a 4° por bordo em sua aplicação, sujeito à Administração.")
    elif not limite_ok:st.error(f"Ângulo excede o limite de {limite}° informado: registro bloqueado.")
    if st.button("Registrar condição experimental simulada",disabled=not (ok and limite_ok),type="primary"):
        rng=np.random.default_rng(2026+len(st.session_state.leituras)) # reprodutível
        estimado,leituras=perturbar(momento,pend,shown,st.session_state.erros,rng)
        tangentes=[p["deflexao_m"]/p["comprimento_m"] for p in leituras]
        theta=degrees(atan(numero_digitado(np.mean(tangentes))))
        angles=[degrees(atan(t)) for t in tangentes]
        item={"numero":len(st.session_state.leituras)+1,"momento_kgm":estimado,"momento_real_kgm":momento,
              "angulo_graus":theta,"tangente":numero_digitado(np.mean(tangentes)),"desacordo_pendulos_graus":max(angles)-min(angles),
              "estavel":True,"fonte":"simulacao_dinamica" if conf else "equilibrio_teorico",
              "instante":datetime.now(timezone.utc).isoformat(),"pendulos":leituras,
              "cenario":copy.deepcopy(st.session_state.erros),"externo_Nm":vento,
              "dinamica":copy.deepcopy(st.session_state.dinamica) if conf else None,
              "indice_movimento":len(st.session_state.movimentos),"parametros_dinamicos":copy.deepcopy(conf),"posicoes_y":copy.deepcopy(st.session_state.prova_y)}
        salvar_leituras([*st.session_state.leituras, item])
        st.success(f"Condição {item['numero']} registrada (resultado simulado)")
    if st.session_state.leituras:
        ultima=st.session_state.leituras[-1]
        if ultima.get("pendulos"):
            with st.expander("Leitura mais recente por instrumento"):
                st.dataframe(ultima["pendulos"],hide_index=True)
                st.caption(f"Desacordo angular entre pêndulos: {ultima['desacordo_pendulos_graus']:.5f}°")
    if st.button("Retornar pesos às posições iniciais"):
        origem = dict(curr)
        st.session_state.prova_y={c["id"]:c["y_m"] for c in ref}
        st.session_state.movimentos.append({"acao":"Retorno a zero","antes":origem,"depois":dict(st.session_state.prova_y),
                                            "momento_kgm":0.,"instante":datetime.now(timezone.utc).isoformat()})
        st.rerun()
    st.subheader("Histórico registrado")
    if st.session_state.leituras:st.dataframe(pd.DataFrame([{k:v for k,v in row.items() if k not in ("pendulos","posicoes_y")} for row in st.session_state.leituras]),width="stretch")
    if st.session_state.movimentos:st.dataframe(pd.DataFrame(st.session_state.movimentos),width="stretch")
    if st.button("Encerrar prova (manter leituras)"):
        st.session_state.prova_em_andamento=False
        from utils.navegacao import ARQUIVOS
        st.switch_page(ARQUIVOS["processamento"])


render()

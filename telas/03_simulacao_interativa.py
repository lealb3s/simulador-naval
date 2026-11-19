from utils.navegacao import selecionar_carga
from utils.navegacao import atalho
import copy
import streamlit as st
from modules.carregamento import calcular
from modules.validacao import verificar_carga
from modules.hidrostatica import consultar,trim_estatico
from modules.estabilidade import avaliar,gz_adaptada
from visualization.casco import planta, cores_categorias
from visualization.inclinacao import secao
from modules.criterios import banda_inicial
from visualization.cargas import perfil
from components.cargo_drag import drag
from utils.estado import inicializar,aplicar,historico,restaurar_cargas

def render():
    inicializar();st.title("Movimentação de cargas")
    if st.session_state.prova_em_andamento:
        st.info("A condição está congelada durante a prova. Encerre o ensaio para voltar a editar.")
        atalho("ensaio", "Retomar o ensaio ativo")
        return
    st.write("Confira a distribuição das cargas. Para ajustar uma posição, arraste o marcador na planta ou informe as coordenadas. Se as posições já estiverem corretas, continue para o planejamento.")
    barco=st.session_state.barco;cargas=st.session_state.cargas
    if not cargas:
        st.info("Adicione uma carga para ver sua posição e movimentá-la.")
        atalho("cargas", "Cadastrar carga")
        return
    if not barco.get("L_m") or not barco.get("B_m"):
        st.warning("Informe comprimento L e boca B em Embarcação para habilitar arraste gráfico.")
    else:
        try:
            cores = cores_categorias(cargas)
            result=drag([{"id":c["id"],"nome":c["nome"],"cor":cores[c["categoria"]],"x_m":c["x_m"],"y_m":c["y_m"]} for c in cargas],barco["L_m"],barco["B_m"],key=f"drag_{st.session_state.get('geracao_drag',0)}",contorno=barco.get("casco_contorno"))
            if result and result.get("nonce")!=st.session_state.get("ultimo_drag"):
                st.session_state.ultimo_drag=result.get("nonce")
                new=copy.deepcopy(cargas)
                for c in new:
                    if c["id"]==result["id"]:
                        st.session_state["carga_escolhida"] = c["id"]
                        if c["x_m"] == result["x_m"] and c["y_m"] == result["y_m"]:
                            break
                        c["x_m"]=round(float(result["x_m"]),8)
                        c["y_m"]=round(float(result["y_m"]),8)
                        verificar_carga(c,barco)
                        aplicar(novas_cargas=new,descricao="Arrastar "+c["nome"])
                        st.rerun()
        except ValueError as ex:
            st.session_state["ultimo_erro_drag"]="Posição recusada. "+str(ex)
            st.session_state["geracao_drag"]=st.session_state.get("geracao_drag",0)+1
            st.rerun()
    if st.session_state.get("ultimo_erro_drag"):
        st.warning(st.session_state.pop("ultimo_erro_drag"))
    ids=[c["id"] for c in cargas]
    if st.session_state.get("carga_escolhida") not in ids:
        st.session_state["carga_escolhida"] = ids[0]
    nomes = {c["id"]:f"{c['nome']} · {c['id']}" for c in cargas}
    choice=st.selectbox("Carga a editar", ids, format_func=nomes.get, key="carga_escolhida")
    c=next(c for c in cargas if c["id"]==choice)
    with st.form(f"ajustar_{choice}_{st.session_state.revisao_cargas}"):
        cols=st.columns(4)
        x=cols[0].number_input("X (m)",value=float(c["x_m"]),format="%.5f")
        y=cols[1].number_input("Y (m)",value=float(c["y_m"]),format="%.5f")
        z=cols[2].number_input("Z (m)",value=float(c["z_m"]),format="%.5f")
        massa=cols[3].number_input("Massa (kg)",value=float(c["massa_kg"]),min_value=0.000001,format="%.5f")
        if st.form_submit_button("Aplicar posição e massa"):
            try:
                novo=copy.deepcopy(cargas)
                for item in novo:
                    if item["id"]==choice:item.update(x_m=x,y_m=y,z_m=z,massa_kg=massa);verificar_carga(item,barco)
                aplicar(novas_cargas=novo,descricao="Mover/alterar massa "+c["nome"])
                st.rerun()
            except ValueError as ex:st.error(str(ex))
    try:
        cond=calcular(barco,cargas)
        a,b,c=st.columns(3)
        a.metric("Δ (kg)",f"{cond['deslocamento_kg']:.3f}")
        b.metric("KG (m)",f"{cond['kg_m']:.4f}" if cond['kg_m'] is not None else "Sem CG base")
        c.metric("TCG (m)",f"{cond['tcg_m']:.4f}" if cond['tcg_m'] is not None else "Sem CG base")
        st.plotly_chart(planta(barco,cargas,cond,choice),width="stretch")

        try:
            hidro=consultar(barco,cond["deslocamento_kg"])
            est=avaliar(barco,cond,hidro)
            trim=trim_estatico(cond,hidro)
            atual = {**barco, "calado_m":hidro.get("calado_m")}
            st.plotly_chart(perfil(atual,cargas,cond),width="stretch")
            st.caption(hidro["metodo"])
            a,b,c=st.columns(3)
            a.metric("KM atualizado (m)",f"{hidro['km_m']:.4f}" if hidro.get('km_m') is not None else "Sem dados")
            b.metric("GM efetivo (m)",f"{est['gm_efetivo_m']:.4f}" if est['gm_efetivo_m'] is not None else "FSM/KG/KM ausente")
            c.metric("Trim linear estimado (m)",f"{trim['variacao_trim_m']:.4f}" if trim['variacao_trim_m'] is not None else "MCT/LCB ausentes")
            a,b,c=st.columns(3)
            for col, titulo, valor in [(a,"Calado (m)",hidro.get("calado_m")), (b,"LCG (m)",cond.get("lcg_m"))]:
                col.metric(titulo, "—" if valor is None else f"{valor:.4f}")
            phi = banda_inicial(cond["tcg_m"],est["gm_efetivo_m"])
            c.metric("Banda estática (°)", "—" if phi is None else f"{phi:+.3f}")
            if est["gm_efetivo_m"] is not None and est["gm_efetivo_m"] <= 0:
                st.warning("GM efetivo não positivo. A condição direita não tem rigidez restauradora inicial positiva.")
            elif phi is None:
                st.info("Para estimar banda, o modelo exige TCG, GM efetivo positivo e resultado até 4°. Para ângulos maiores, consulte dados de estabilidade da condição.")
            else:
                st.caption("Estabilidade transversal inicial positiva. O cálculo de banda pressupõe casco simétrico, trim pequeno e ausência de momento externo.")
                figura=secao(atual,phi,cond["kg_m"],hidro.get("kb_m"),hidro.get("km_m"),cond["tcg_m"])
                if figura is not None:
                    st.plotly_chart(figura,width="stretch")
            if barco.get("gz_curva"):
                import plotly.express as px
                try:
                    gz=gz_adaptada(barco,cond)
                    st.plotly_chart(px.line(gz,x="angulo_graus",y="gz_m",title="GZ adaptada ao KG (somente mesma condição de Δ, TCG=0 e FSM=0)"),width="stretch")
                except ValueError as ex:st.info("GZ não adaptada: "+str(ex))
        except ValueError as ex:
            st.warning("Hidrostática não atualizada: "+str(ex))
            st.plotly_chart(perfil({**barco,"calado_m":None},cargas,cond),width="stretch")
    except ValueError as ex:st.warning(str(ex))
    atalho("cargas", "Adicionar, duplicar ou retirar cargas")
    c1,c2,c3=st.columns(3)
    if c1.button("Desfazer"):historico("undo");st.rerun()
    if c2.button("Refazer"):historico("redo");st.rerun()
    if c3.button("Restaurar condição inicial",disabled=st.session_state.cargas_inicio is None):restaurar_cargas();st.rerun()


render()

"""Arraste compartilhado entre cadastro e movimentação."""
import copy
import streamlit as st
from components import cargo_drag
from modules.validacao import verificar_carga
from utils.estado import aplicar
from visualization.casco import cores_categorias


def planta_editavel(barco,cargas,local):
    if not barco.get("L_m") or not barco.get("B_m"):
        st.warning("Informe comprimento L e boca B em Embarcação para habilitar arraste gráfico.")
    else:
        try:
            cores = cores_categorias(cargas)
            result=cargo_drag.drag([{"id":c["id"],"nome":c["nome"],"cor":cores[c["categoria"]],"x_m":c["x_m"],"y_m":c["y_m"],"comp_m":c.get("comp_m"),"larg_m":c.get("larg_m")} for c in cargas],barco["L_m"],barco["B_m"],key=f"drag_{local}_{st.session_state.get('geracao_drag',0)}",contorno=barco.get("casco_contorno"))
            if result and result.get("nonce")!=st.session_state.get("ultimo_drag_"+local):
                st.session_state["ultimo_drag_"+local]=result.get("nonce")
                new=copy.deepcopy(cargas)
                for c in new:
                    if c["id"]==result["id"]:
                        st.session_state["carga_escolhida"] = c["id"]
                        if c["x_m"] == result["x_m"] and c["y_m"] == result["y_m"]:
                            break
                        c["x_m"]=float(result["x_m"])
                        c["y_m"]=float(result["y_m"])
                        verificar_carga(c,barco)
                        aplicar(novas_cargas=new,descricao="Arrastar "+c["nome"])
                        st.rerun()
        except ValueError as ex:
            st.session_state["ultimo_erro_drag"]="Posição recusada. "+str(ex)
            st.session_state["geracao_drag"]=st.session_state.get("geracao_drag",0)+1
            st.rerun()
    if st.session_state.get("ultimo_erro_drag"):
        st.warning(st.session_state.pop("ultimo_erro_drag"))

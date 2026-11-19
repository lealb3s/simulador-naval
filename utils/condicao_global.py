"""Importa uma linha de condição global, preservando o cadastro individual de cargas."""
import json

import streamlit as st
import pandas as pd

from modules.carregamento import base_da_condicao
from utils.dados import numero_localizado
from utils.estado import aplicar
from utils.importacao import ler_tabela, verificar_unidade_declarada
from utils.ui_importacao import controles_tabela, mapear_campos, aplicar_mapeamento, selecionar_unidade


def painel(entrada=None, selecao=None):
    campos = ["deslocamento_kg","lcg_m","tcg_m","kg_m"]
    with st.expander("Importar condição global de carregamento", expanded=entrada is not None):
        st.write("Use esta opção para uma tabela com deslocamento, LCG, TCG e KG totais. Cadastre antes as cargas individuais já incluídas no total. Elas serão descontadas ao calcular a massa base.")
        arquivo=entrada if entrada is not None else st.file_uploader("Tabela de condições de carga",type=["csv","xlsx","json"],key="condicao_global_upload")
        if arquivo is None:
            return
        try:
            import hashlib
            uid=hashlib.sha1(arquivo.getvalue()).hexdigest()[:10]
            aba,head,virgula,_=selecao if selecao is not None else controles_tabela(arquivo,"global",("global",))
            if arquivo.name.lower().endswith(".json"):
                dados=json.loads(arquivo.getvalue().decode("utf-8-sig"))
                if isinstance(dados,dict):
                    dados=dados.get("condicoes",[dados])
            else:
                dados=ler_tabela(arquivo,aba=aba,cabecalho_linha=head)
            if not isinstance(dados,list) or not dados or not all(isinstance(r,dict) for r in dados):
                raise ValueError("Use uma linha por condição com quatro grandezas numéricas.")
            st.dataframe(pd.DataFrame(dados).head(20),hide_index=True)
            prefixo=f"global_{uid}_{aba}_{head}"
            mapa=mapear_campos(dados,"global",campos,campos,prefixo)
            a,b=st.columns(2)
            um=selecionar_unidade(a,"Unidade do deslocamento total",["Selecione","kg","t (tonelada métrica)"],mapa,campos[:1],prefixo+"_massa")
            ul=selecionar_unidade(b,"Unidade dos centros globais",["Selecione","m","cm","mm"],mapa,campos[1:],prefixo+"_comprimento")
            indice=st.selectbox("Linha da condição",range(len(dados)),format_func=lambda i:str(dados[i].get("__linha_origem__",i+1)))
            if st.button("Importar condição e calcular massa base"):
                linha=aplicar_mapeamento([dados[indice]],mapa,campos)[0]
                if "Selecione" in (um,ul):
                    raise ValueError("Confirme as unidades da condição de carga.")
                valores={}
                for k in campos:
                    unidade=("kg" if um=="kg" else "t") if k==campos[0] else ul
                    verificar_unidade_declarada(mapa[k],unidade,k)
                    valores[k]=numero_localizado(linha[k],k,virgula)*{"kg":1,"t":1000,"m":1,"cm":.01,"mm":.001}[unidade]
                nova=base_da_condicao(valores["deslocamento_kg"],valores,st.session_state.cargas)
                aplicar(novo_barco={**st.session_state.barco,**nova},descricao="Importar condição global com desconto das cargas cadastradas")
                st.success(f"Condição importada. Massa base remanescente de {nova['massa_base_kg']:.4g} kg.")
        except (TypeError,ValueError,KeyError) as exc:
            st.error(str(exc))

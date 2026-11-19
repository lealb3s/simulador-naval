"""Controles Streamlit compartilhados para CSV/XLSX.

A tela só sugere categoria e campos; o usuário confirma unidades e importação.
"""
import hashlib
import io
import re
from .navegacao import ARQUIVOS
import streamlit as st
import pandas as pd
from .importacao import inspecionar_abas, ler_bruto, escolher_cabecalho
from .mapeamento import sugestao_coluna

NOMES_TIPO={'global':'Condição global de carga','hidro':'Tabela hidrostática', 'barco':'Dados principais da embarcação',
            'gz':'Curva GZ', 'casco':'Contorno XY', 'cargas':'Cargas',
            'leituras':'Medições experimentais'}


def transferir_aba(arquivo, destino, aba, cabecalho, virgula):
    st.session_state[f"tabela_para_{destino}"] = {
        "nome": arquivo.name, "dados": arquivo.getvalue(), "aba": aba,
        "cabecalho": cabecalho, "virgula": virgula,
    }
    st.switch_page(ARQUIVOS[destino])


def arquivo_recebido(local, destino):
    chave = f"tabela_para_{destino}"
    if local is not None:
        st.session_state.pop(chave, None)
        return local
    recebido = st.session_state.get(chave)
    if recebido:
        st.caption(f"Arquivo selecionado em Embarcação · {recebido['nome']}")
        if st.button("Dispensar arquivo", key=f"dispensar_{destino}"):
            st.session_state.pop(chave)
            st.rerun()
        entrada = io.BytesIO(recebido["dados"])
        entrada.name = recebido["nome"]
        return entrada


@st.cache_data(show_spinner=False, max_entries=12, ttl=600)
def _inspecionar(nome, dados):
    entrada = io.BytesIO(dados)
    entrada.name = nome
    return inspecionar_abas(entrada)


def controles_tabela(uploaded, prefix, categorias=()):
    uid = hashlib.sha1(uploaded.getvalue()).hexdigest()[:10]
    ext = uploaded.name.lower()
    aba = None
    recebido = st.session_state.get(f"tabela_para_{prefix}", {})
    if ext.endswith(".json"):
        return None, None, False, None
    if ext.endswith(".xlsx"):
        infos = _inspecionar(uploaded.name, uploaded.getvalue())
        abas = [r["aba"] for r in infos]
        if not abas:
            raise ValueError("A pasta de trabalho está vazia.")
        primeira = next((r["aba"] for r in infos if r["tipo"] in categorias), abas[0])
        padrao = recebido.get("aba") if recebido.get("aba") in abas else primeira
        aba = st.selectbox("Aba do Excel", abas, index=abas.index(padrao), key=f"{prefix}_aba_{uid}")
        info = next(r for r in infos if r["aba"] == aba)
        header, categoria = info["linha_cabecalho"], info["tipo"]
        st.caption(" · ".join(f"{r['aba']} ({NOMES_TIPO.get(r['tipo'], 'revisar cabeçalho')})" for r in infos))
    raw = ler_bruto(uploaded, aba=aba, nrows=38)
    if aba is None:
        header, categoria = escolher_cabecalho(raw)
    if recebido and recebido["aba"] == aba and recebido["cabecalho"] is not None:
        header = recebido["cabecalho"]
    cab = st.number_input("Linha do cabeçalho", min_value=1, max_value=100000,
                          value=header+1, step=1, key=f"{prefix}_cabecalho_{uid}_{aba}") - 1
    amostra = raw.iloc[cab + 1:].to_numpy().flat
    virgula = any(isinstance(v, str) and re.fullmatch(r"[+-]?[0-9.]+,[0-9]+", v.strip())
                  for v in amostra)
    if recebido and recebido["aba"] == aba:
        virgula = recebido["virgula"]
    decimal = st.checkbox("Usar vírgula decimal nos números em texto",
                          value=virgula, key=f"{prefix}_virgula_{uid}_{aba}")
    return aba, cab, decimal, categoria if cab == header else None


def mapear_campos(dados,tipo,colunas,obrigatorios,prefix):
    nomes=list(dict.fromkeys(k for r in dados if isinstance(r,dict) for k in r if k!='__linha_origem__'))
    if not nomes:raise ValueError('Não existem colunas com nome nessa aba.')
    st.caption('Colunas detectadas: '+', '.join(nomes))
    # Exige confirmação de toda correspondência, com pré-seleção apenas de aliases exatos.
    escolhas=['— Não importar —']+nomes
    colunas_map={}
    ca,cb=st.columns(2)
    for i,c in enumerate(colunas):
        sugerido=sugestao_coluna(tipo,c,nomes)
        default=nomes.index(sugerido)+1 if sugerido is not None else 0
        with (ca if i%2==0 else cb):
            colunas_map[c]=st.selectbox(c+(' *' if c in obrigatorios else ' (opcional)'),
                         escolhas,index=default,key=f'{prefix}_{tipo}_{c}')
    st.caption('* Campo obrigatório. Uma mesma coluna de origem não pode representar dois campos.')
    return colunas_map


def aplicar_mapeamento(dados,colmap,obrigatorios):
    ausentes=[x for x in obrigatorios if colmap.get(x)=='— Não importar —']
    if ausentes:
        raise ValueError('Associe as colunas obrigatórias: '+', '.join(ausentes))
    usados=[x for x in colmap.values() if x!='— Não importar —']
    if len(usados)!=len(set(usados)):
        raise ValueError('A mesma coluna foi usada para duas grandezas. Revise o mapeamento.')
    return [dict({'__linha_origem__':r.get('__linha_origem__')},
                 **{c:r.get(s) if s!='— Não importar —' else None for c,s in colmap.items()})
            for r in dados]


def selecionar_unidade(container, rotulo, opcoes, mapeamento, campos, chave):
    from .importacao import unidade_declarada
    unidades = {unidade_declarada(mapeamento[c]) for c in campos
                if mapeamento.get(c) and mapeamento[c] != "— Não importar —"}
    padrao = unidades.pop() if len(unidades) == 1 else None
    if padrao == "t":
        padrao = "t (tonelada métrica)"
    indice = opcoes.index(padrao) if padrao in opcoes else 0
    return container.selectbox(rotulo, opcoes, index=indice, key=chave)

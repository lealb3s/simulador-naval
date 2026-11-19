"""Controles Streamlit compartilhados para CSV/XLSX.

A tela só sugere categoria e campos; o usuário confirma unidades e importação.
"""
import hashlib
import io
import re
from .navegacao import ARQUIVOS
import streamlit as st
import pandas as pd
from .importacao import inspecionar_abas, ler_bruto, escolher_cabecalho, LayoutTabela, selecionar_bloco
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


def fonte_tabela(rotulo, prefixo, chave_upload=None):
    modo=st.radio("Entrada da tabela",["Enviar arquivo","Digitar ou colar"],horizontal=True,key=prefixo+"_fonte")
    if modo=="Enviar arquivo":
        return st.file_uploader(rotulo,type=["csv","xlsx","json"],key=chave_upload or prefixo+"_upload")
    texto=st.text_area("Tabela manual",help="Copie as células do Excel ou digite uma linha por registro, separando colunas por ponto e vírgula.",
                       placeholder="Digite ou cole as células da sua tabela",key=prefixo+"_texto")
    if texto.strip():
        entrada=io.BytesIO(texto.encode("utf-8"))
        entrada.name="tabela_manual.csv"
        return entrada


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
    chave=f"{prefix}_{uid}_{aba}"
    anterior=recebido.get("cabecalho") if recebido.get("aba")==aba else None
    anterior_layout=anterior if isinstance(anterior,LayoutTabela) else LayoutTabela()
    avancado=st.checkbox("Ajustar formato da tabela",value=isinstance(anterior,LayoutTabela),key=chave+"_custom")
    intervalo=""
    transposta=False
    separador=None
    sem_titulo=False
    if avancado:
        if ext.endswith(".csv"):
            opcoes={"Automático":None,"Ponto e vírgula":";","Vírgula":",","Tabulação":"\t","Barra vertical":"|"}
            valor=st.selectbox("Separador das colunas",list(opcoes),index=list(opcoes.values()).index(anterior_layout.separador),key=chave+"_sep")
            separador=opcoes[valor]
        intervalo=st.text_input("Intervalo de células",anterior_layout.intervalo,placeholder="Ex.: B3:G15 (vazio usa toda a tabela)",key=chave+"_range")
        transposta=st.checkbox("Cada registro ocupa uma coluna (transpor)",value=anterior_layout.transposta,key=chave+"_trans")
        sem_titulo=st.checkbox("Tabela sem cabeçalho",value=anterior_layout.cabecalho==-1,key=chave+"_sem")
    raw=ler_bruto(uploaded,aba=aba,nrows=None if avancado else 38,separador=separador)
    raw=selecionar_bloco(raw,intervalo,transposta)
    if raw.empty:
        raise ValueError("Não há células no bloco escolhido.")
    if avancado:
        st.caption("Prévia do bloco escolhido. A linha do cabeçalho é contada dentro desta prévia.")
        preview=raw.head(12).reset_index(drop=True).copy()
        preview.index+=1
        st.dataframe(preview.astype(str),width="stretch")
    header,categoria=escolher_cabecalho(raw.reset_index(drop=True))
    if anterior is not None:
        header=anterior.cabecalho if isinstance(anterior,LayoutTabela) else anterior
    cab=-1 if sem_titulo else st.number_input("Linha do cabeçalho",min_value=1,max_value=100000,value=max(1,header+1),
                      step=1,key=f"{prefix}_cabecalho_{uid}_{aba}_{intervalo}_{transposta}")-1
    amostra = raw.iloc[cab + 1:].to_numpy().flat
    virgula = any(isinstance(v, str) and re.fullmatch(r"[+-]?[0-9.]+,[0-9]+", v.strip())
                  for v in amostra)
    if recebido and recebido["aba"] == aba:
        virgula = recebido["virgula"]
    decimal = st.checkbox("Usar vírgula decimal nos números em texto",
                          value=virgula, key=f"{prefix}_virgula_{uid}_{aba}")
    layout=LayoutTabela(cab,intervalo,transposta,separador) if avancado else cab
    return aba, layout, decimal, categoria if cab == header else None


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

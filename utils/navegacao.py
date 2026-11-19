"""Sequência compartilhada pelo menu, atalhos e rodapé."""
import streamlit as st

ETAPAS = [
    ("embarcacao", "Embarcação", "01_embarcacao", "directions_boat"),
    ("cargas", "Carregamento", "02_carregamento", "inventory_2"),
    ("movimentacao", "Movimentação", "03_simulacao_interativa", "open_with"),
    ("planejamento", "Planejamento de pesos", "04_planejamento_pesos", "balance"),
    ("pendulos", "Pêndulos", "05_pendulos", "straighten"),
    ("condicoes", "Condições do ensaio", "07_simulacao_erros", "tune"),
    ("ensaio", "Ensaio virtual", "06_prova_inclinacao", "science"),
    ("processamento", "Processamento", "08_processamento", "show_chart"),
    ("relatorio", "Relatório", "09_relatorio", "description"),
]
ARQUIVOS = {k: f"telas/{arquivo}.py" for k, _, arquivo, _ in ETAPAS}


def atalho(etapa, texto):
    st.page_link(ARQUIVOS[etapa], label=texto, icon=":material/arrow_forward:")


def rodape(indice):
    st.divider()
    anterior, proxima = st.columns(2)
    with anterior:
        if indice:
            chave, nome, *_ = ETAPAS[indice - 1]
            st.page_link(ARQUIVOS[chave], label=f"Voltar · {nome}", icon=":material/arrow_back:")
        else:
            st.page_link("inicio.py", label="Voltar ao início", icon=":material/arrow_back:")
    with proxima:
        if indice + 1 < len(ETAPAS):
            chave, nome, *_ = ETAPAS[indice + 1]
            atalho(chave, f"Continuar · {nome}")
        else:
            st.page_link("inicio.py", label="Resumo da sessão", icon=":material/home:")


def selecionar_carga(rotulo, cargas, container=st):
    """Exibe nomes, distinguindo cargas homônimas pelo identificador."""
    from collections import Counter
    nomes = Counter(c["nome"] for c in cargas)
    opcoes = {f"{c['nome']} · {c['id']}": c["id"] for c in cargas}
    if all(q == 1 for q in nomes.values()):
        opcoes = {c["nome"]: c["id"] for c in cargas}
    return opcoes[container.selectbox(rotulo, list(opcoes))]

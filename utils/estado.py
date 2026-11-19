"""Persistência por sessão: histórico de edição e log de ensaio separados."""
import copy
import uuid
from datetime import datetime,timezone
import streamlit as st
from .dados import registro_vazio


def dados_iniciais():
    return {"revisao_barco":0, "revisao_cargas":0, "revisao_leituras":0, "barco":registro_vazio(),"cargas":[],"cargas_inicio":None,"undo":[],"redo":[],
              "log_alteracoes":[],"leituras":[],"movimentos":[],"pesos_inicio":None,
              "pendulos":[{"id":"P1","comprimento_m":None},{"id":"P2","comprimento_m":None}],
              "configuracoes":[],"erros":{},"dinamica":None,"dinamica_config":None,
              "prova_offset":{},"prova_em_andamento":False}


def inicializar():
    for k,v in dados_iniciais().items():
        if k not in st.session_state: st.session_state[k]=copy.deepcopy(v)


# Somente dados salvos do projeto. Widgets e rascunhos pertencem à tela ativa.
CAMPOS_OPCIONAIS = {
    "condicao_ensaio", "config_pendulos", "limites_planejamento", "tabela_planejamento",
    "param_regressao", "ultima_regressao", "estudo_sensibilidade", "prova_y",
    "serie_dinamica", "tabelas_livres", "tabela_para_cargas", "tabela_para_processamento",
}


def alternar_projeto(usar_exemplo):
    """Alterna entre dois projetos independentes na mesma sessão do navegador."""
    sessao = st.session_state
    exemplo_atual = bool(sessao.get("exemplo_ativo"))
    if exemplo_atual == usar_exemplo:
        return
    campos = set(dados_iniciais()) | CAMPOS_OPCIONAIS
    anterior = {k:sessao[k] for k in campos if k in sessao}
    destino = sessao.get("_projeto_inativo")
    if destino is None:
        destino = dados_iniciais()
        if usar_exemplo:
            from .exemplo import dados_do_exemplo
            destino.update(dados_do_exemplo())
    for chave in list(sessao):
        del sessao[chave]
    sessao.update(destino)
    sessao["_projeto_inativo"] = anterior
    sessao.exemplo_ativo = usar_exemplo


def snapshot():
    return copy.deepcopy({k:st.session_state[k] for k in ("barco","cargas")})


def aplicar(novo_barco=None, novas_cargas=None, descricao="Alteração"):
    if novo_barco is not None:
        st.session_state.revisao_barco += 1
    if novas_cargas is not None:
        st.session_state.revisao_cargas += 1
    limpar_resultados()
    st.session_state.pop("tabela_planejamento", None)
    anterior=snapshot()
    st.session_state.undo.append(anterior)
    st.session_state.redo=[]
    if novo_barco is not None:st.session_state.barco=copy.deepcopy(novo_barco)
    if novas_cargas is not None:st.session_state.cargas=copy.deepcopy(novas_cargas)
    st.session_state.log_alteracoes.append({"evento":descricao,"id":str(uuid.uuid4()),
        "instante_utc":datetime.now(timezone.utc).isoformat(),"antes":anterior,"depois":snapshot()})


def historico(acao):
    fonte, destino=("undo","redo") if acao=="undo" else ("redo","undo")
    if not st.session_state[fonte]:return False
    anterior=snapshot()
    st.session_state[destino].append(anterior)
    st.session_state.revisao_barco += 1
    st.session_state.revisao_cargas += 1
    st.session_state.pop("tabela_planejamento", None)
    limpar_resultados()
    antigo=st.session_state[fonte].pop()
    st.session_state.barco=antigo["barco"]
    st.session_state.cargas=antigo["cargas"]
    st.session_state.log_alteracoes.append({"evento":acao,"id":str(uuid.uuid4()),
        "instante_utc":datetime.now(timezone.utc).isoformat(),"antes":anterior,"depois":snapshot()})
    return True


def restaurar_cargas():
    if st.session_state.cargas_inicio is None:
        raise ValueError("Salve primeiro uma condição inicial em Carregamento")
    aplicar(novas_cargas=copy.deepcopy(st.session_state.cargas_inicio),descricao="Restaurar cargas iniciais")


def nova_id():return uuid.uuid4().hex[:10]


def limpar_resultados():
    for key in ("ultima_regressao", "param_regressao","estudo_sensibilidade"):
        st.session_state.pop(key, None)


def salvar_leituras(leituras):
    st.session_state.leituras = leituras
    st.session_state.revisao_leituras += 1
    limpar_resultados()

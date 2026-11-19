import streamlit as st

from modules.carregamento import calcular
from utils.navegacao import atalho

s = st.session_state
st.title("Prova de inclinação")
st.write("Prepare a embarcação, mova um peso entre bordos e acompanhe como a deflexão dos pêndulos permite estimar GM e KG.")
virtual, real = st.columns(2)
with virtual.container(border=True):
    st.subheader("Simular um ensaio")
    st.write("Comece pela massa e pelos centros da embarcação. Depois, cadastre as cargas e configure os instrumentos.")
    if s.prova_em_andamento:
        atalho("ensaio", "Retomar ensaio virtual")
    else:
        atalho("embarcacao", "Abrir embarcação")
with real.container(border=True):
    st.subheader("Usar medições reais")
    st.write("Se você já tem momentos e leituras dos pêndulos, importe a tabela e informe o deslocamento da condição ensaiada.")
    atalho("processamento", "Abrir processamento")

with st.container(border=True):
    st.subheader("Experimentar com um pontão fictício")
    st.write("O caso tem dois pesos de 250 kg e dois pêndulos já dimensionados. Mova um peso, volte ao zero e compare o GM medido com 1,000 m.")
    sessao_ocupada = bool(s.log_alteracoes or s.leituras or s.movimentos or s.erros or s.get("config_pendulos") or s.configuracoes)
    autorizado = not sessao_ocupada
    if sessao_ocupada and not s.prova_em_andamento:
        autorizado = st.checkbox("Substituir os dados desta sessão pelo exemplo fictício")
    if st.button("Carregar exemplo fictício", disabled=s.prova_em_andamento or not autorizado):
        from copy import deepcopy
        from utils.exemplo import exemplo
        from utils.estado import inicializar
        from utils.navegacao import ARQUIVOS
        barco, cargas = exemplo()
        for chave in list(s):
            del s[chave]
        inicializar()
        s.barco, s.cargas = barco, cargas
        s.cargas_inicio = deepcopy(cargas)
        s.pendulos = [{"id":"P1","comprimento_m":2.0},{"id":"P2","comprimento_m":2.5}]
        s.config_pendulos = {"ang":2.0,"res":.001,"alt":2.5}
        s.erros = {"limite_angulo_graus":4.0}
        s.configuracoes = [{"massa_kg":250,"quantidade":n,"distancia_m":d,"pendulo_m":l,"y_inicial_m":0.0}
                           for n,d,l in [(1,1.25,2.0),(2,1.0,2.25),(2,1.25,2.5)]]
        s.limites_planejamento = {"lim_ang":"4","max_p":"2,5","res_p":"0,001","lim_massa":"250"}
        s.exemplo_ativo = True
        st.switch_page(ARQUIVOS["movimentacao"])

st.subheader("Condição da sessão")
st.caption(s.barco.get("nome") or "Embarcação sem identificação")
try:
    condicao = calcular(s.barco, s.cargas)
except ValueError:
    condicao = {}
a, b, c = st.columns(3)
delta = condicao.get("deslocamento_kg")
a.metric("Deslocamento", "—" if delta is None else f"{delta:.3f} kg")
b.metric("Cargas cadastradas", len(s.cargas))
c.metric("Leituras registradas", len(s.leituras))
if condicao:
    from modules.hidrostatica import consultar
    from modules.estabilidade import avaliar
    with st.expander("Centros de gravidade e estabilidade"):
        cg, tcg, gm = st.columns(3)
        for coluna, campo, nome in [(cg, "kg_m", "KG"), (tcg, "tcg_m", "TCG")]:
            valor = condicao.get(campo)
            coluna.metric(nome, "—" if valor is None else f"{valor:.4f} m")
        try:
            hidro = consultar(s.barco, delta)
            valor = avaliar(s.barco, condicao, hidro)["gm_efetivo_m"]
            gm.metric("GM efetivo", "—" if valor is None else f"{valor:.4f} m")
            st.caption(hidro["metodo"])
        except ValueError as erro:
            st.caption(str(erro))
if s.leituras:
    atalho("relatorio", "Exportar dados da sessão")
st.caption("As etapas usam a mesma sessão. Salve as alterações em cada formulário antes de avançar. Em Relatório, você pode baixar os dados e os resultados.")

from pathlib import Path
with st.expander("Fundamentação dos cálculos"):
    st.markdown(Path(__file__).with_name("REFERENCIAS.md").read_text(encoding="utf-8"))

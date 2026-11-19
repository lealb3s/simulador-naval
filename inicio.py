import streamlit as st

from modules.carregamento import calcular
from utils.navegacao import ARQUIVOS, atalho
from utils.estado import alternar_projeto

s = st.session_state
st.title("Prova de inclinação")
st.write("Prepare a embarcação, mova um peso entre bordos e acompanhe como a deflexão dos pêndulos permite estimar GM e KG.")
virtual, real = st.columns(2)
with virtual.container(border=True):
    st.subheader("Simular um ensaio")
    st.write("Comece pela massa e pelos centros da embarcação. Depois, cadastre as cargas e configure os instrumentos.")
    if st.button("Abrir entrada manual",type="primary"):
        alternar_projeto(False)
        st.switch_page(ARQUIVOS["embarcacao"])
    if s.prova_em_andamento:
        atalho("ensaio", "Retomar ensaio virtual")
with real.container(border=True):
    st.subheader("Usar medições reais")
    st.write("Se você já tem momentos e leituras dos pêndulos, importe a tabela e informe o deslocamento da condição ensaiada.")
    atalho("processamento", "Abrir processamento")

with st.container(border=True):
    st.subheader("Experimentar com um pontão fictício")
    st.write("O caso tem dois pesos de 250 kg e dois pêndulos já dimensionados. Mova um peso, volte ao zero e compare o GM medido com 1,000 m.")
    if st.button("Carregar exemplo fictício" if not s.get("exemplo_ativo") else "Continuar no exemplo"):
        alternar_projeto(True)
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

import streamlit as st

from utils.estado import inicializar
from utils.navegacao import ARQUIVOS, ETAPAS, rodape

st.set_page_config(page_title="Prova de inclinação", page_icon="⚓", layout="wide")
inicializar()
inicio = st.Page("inicio.py", title="Início", icon=":material/home:", default=True)
paginas = [st.Page(ARQUIVOS[chave], title=nome, icon=f":material/{icone}:",
                   url_path=arquivo.split("_", 1)[1])
           for chave, nome, arquivo, icone in ETAPAS]
pagina = st.navigation({
    "Simulador": [inicio],
    "Modo de carregamento": paginas[:3],
    "Modo de prova de inclinação": paginas[3:7],
    "Resultados": paginas[7:],
})
if pagina.url_path == inicio.url_path:
    pagina.run()
else:
    indice = next(i for i, p in enumerate(paginas) if p.url_path == pagina.url_path)
    st.progress((indice + 1) / len(paginas), text=f"Etapa {indice + 1} de {len(paginas)}")
    pagina.run()
    rodape(indice)

from pathlib import Path
with st.sidebar.expander("Fundamentação dos cálculos"):
    st.download_button("Baixar equações e referências", Path(__file__).with_name("REFERENCIAS.md").read_bytes(),
                       file_name="REFERENCIAS.md", mime="text/markdown")

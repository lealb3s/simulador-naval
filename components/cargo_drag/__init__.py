"""Componente Streamlit bidirecional para arrastar pontos de cargas na planta.
Fallback: controles numéricos disponíveis sempre na página."""
from pathlib import Path
import streamlit.components.v1 as components
_component=components.declare_component("cargo_drag",path=str(Path(__file__).parent/"frontend"))

def drag(cargas, comprimento, boca, key="drag_pesos", contorno=None):
    return _component(cargas=cargas, comprimento=comprimento, boca=boca,contorno=contorno or [],key=key,default=None)

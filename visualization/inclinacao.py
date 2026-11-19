"""Seção transversal de referência com rotação visual sobre a flutuação direita."""
import numpy as np
import plotly.graph_objects as go


def secao(barco, angulo_graus, kg=None, kb=None, km=None, tcg=0.0):
    boca, pontal, calado = (barco.get(k) for k in ("B_m","D_m","calado_m"))
    if boca is None or pontal is None:
        return None
    pivô = calado if calado is not None else 0.0
    rad = np.deg2rad(angulo_graus)
    # Y positivo a boreste: ângulo positivo submerge o bordo de Y positivo.
    rot = np.array([[np.cos(rad), np.sin(rad)], [-np.sin(rad), np.cos(rad)]])
    def girar(pontos):
        return (np.asarray(pontos) - [0, pivô]) @ rot.T + [0, pivô]

    contorno = girar([[-boca/2,0],[boca/2,0],[boca/2,pontal],[-boca/2,pontal],[-boca/2,0]])
    fig = go.Figure(go.Scatter(x=contorno[:,0], y=contorno[:,1], mode="lines", fill="toself",
                               name="Seção nominal", line_color="#176e80", fillcolor="rgba(23,110,128,.12)"))
    for nome, y, z, cor in (("G",tcg,kg,"#cd503a"),("B direito",0,kb,"#3677b7"),("M inicial",0,km,"#287858")):
        if y is not None and z is not None:
            x1, y1 = girar([[y,z]])[0]
            fig.add_scatter(x=[x1], y=[y1], mode="markers+text", text=[nome], textposition="top right",
                            marker=dict(color=cor,size=10), name=nome)
    if calado is not None:
        fig.add_hline(y=calado,line_dash="dash",annotation_text="Flutuação de referência")
    fig.update_yaxes(scaleanchor="x",scaleratio=1)
    fig.update_layout(title=f"Seção ilustrativa · banda {angulo_graus:.2f}°",
                      xaxis_title="Bombordo (−)  /  Boreste (+)   ·   Y (m)",yaxis_title="Z (m)",height=410)
    return fig

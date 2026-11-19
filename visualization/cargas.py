"""Representação simplificada de cargas e de CG no plano X-Z."""
import plotly.graph_objects as go

def perfil(barco,cargas,condicao=None):
    fig=go.Figure()
    if barco.get("L_m") is not None and barco.get("D_m") is not None:
        L,D=barco["L_m"],barco["D_m"]
        fig.add_trace(go.Scatter(x=[0,L,L,0,0],y=[0,0,D,D,0],mode="lines",name="Envelope nominal (não casco real)"))
    for c in cargas:
        fig.add_trace(go.Scatter(x=[c["x_m"]],y=[c["z_m"]],mode="markers+text",text=[c["nome"]],
                                 textposition="top center",name=c["nome"],marker=dict(size=11)))
    if condicao and condicao.get("lcg_m") is not None and condicao.get("kg_m") is not None:
        fig.add_trace(go.Scatter(x=[condicao["lcg_m"]],y=[condicao["kg_m"]],mode="markers+text",text=["G"],marker=dict(size=13,symbol="x",color="red"),name="G"))
    if barco.get("calado_m") is not None:
        fig.add_hline(y=barco["calado_m"],line_dash="dash",annotation_text="Flutuação da condição direita")
    fig.update_layout(title="Vista longitudinal — posições e G",xaxis_title="X (m)",yaxis_title="Z acima da linha base (m)",height=380)
    return fig

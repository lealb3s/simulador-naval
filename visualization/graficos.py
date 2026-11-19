import plotly.graph_objects as go

def ajuste(info):
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=info["x"],y=info["y"],mode="markers",name="Observações"))
    dados=sorted(zip(info["x"],info["y_ajuste"]))
    fig.add_trace(go.Scatter(x=[v[0] for v in dados],y=[v[1] for v in dados],mode="lines",name="Regressão com intercepto"))
    fig.update_layout(title="tan(θ) vs momento inclinante de massa",xaxis_title="Σ(m·d) (kg·m)",yaxis_title="tan(θ) (adimensional)")
    return fig

def residuos(info):
    fig=go.Figure(go.Scatter(x=info["x"],y=info["residuos"],mode="markers"))
    fig.add_hline(y=0,line_dash="dash")
    fig.update_layout(title="Resíduos da regressão",xaxis_title="Momento (kg·m)",yaxis_title="Resíduo de tan(θ)")
    return fig

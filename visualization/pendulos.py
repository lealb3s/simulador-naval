import plotly.graph_objects as go

def desenhar(pendulos, deflexoes):
    fig=go.Figure()
    for i,p in enumerate(pendulos):
        L=p["comprimento_m"]
        if L is None:continue
        x=deflexoes.get(p["id"],0)
        origem=i*max(1,max((z["comprimento_m"] or 0) for z in pendulos))
        fig.add_trace(go.Scatter(x=[origem,origem+x],y=[0,-L],mode="lines+markers",name=p["id"]))
    fig.update_layout(title="Pêndulos em equilíbrio quase estático (não inclui oscilação própria)",
                      xaxis_title="Deflexão horizontal em escala (m)",yaxis_title="Vertical (m)",height=380)
    fig.update_yaxes(scaleanchor="x",scaleratio=1)
    return fig

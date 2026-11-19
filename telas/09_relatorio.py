import html
import io
import json
import zipfile
from datetime import datetime,timezone
import pandas as pd
import streamlit as st
from utils.relatorio_pdf import gerar_pdf
from utils.estado import inicializar
from utils.dados import json_bytes,csv_bytes,normalizar

inicializar();st.title("Relatório")
st.write("Revise os resultados da condição ensaiada e escolha o formato para exportar.")
s=st.session_state
pacote={k:normalizar(s[k]) for k in ("barco","cargas","leituras","movimentos","pendulos","configuracoes","erros","log_alteracoes")}
pacote["condicao_ensaio"] = normalizar(s.get("condicao_ensaio"))
pacote["ultima_regressao"]=normalizar(s.get("ultima_regressao"))
pacote["param_regressao"]=normalizar(s.get("param_regressao"))
pacote["tabela_planejamento"] = normalizar(s.get("tabela_planejamento", []))
pacote["limites_planejamento"] = normalizar(s.get("limites_planejamento", {}))
pacote["serie_dinamica"] = normalizar(s.get("serie_dinamica", []))
pacote["estudo_sensibilidade"]=normalizar(s.get("estudo_sensibilidade"))
pacote["tabelas_livres"] = dict(s.get("tabelas_livres",{}))
pdf = gerar_pdf(pacote)
st.subheader(s.barco.get("nome") or "Embarcação sem identificação")
reg = s.get("ultima_regressao") or {}
a, b, c = st.columns(3)
a.metric("Leituras registradas", len(s.leituras))
b.metric("GM observado", f"{reg['gm_observado_m']:.4f} m" if reg else "—")
c.metric("KG sólido", f"{reg['kg_solido_m']:.4f} m" if reg.get("kg_solido_m") is not None else "—")
if not reg:
    from utils.navegacao import atalho
    st.caption("O relatório pode ser exportado com dados parciais. Para incluir GM e KG, calcule a regressão.")
    atalho("processamento", "Ir para o cálculo da regressão")


# Relatório HTML autocontido; arquivos de origem em separado para auditabilidade.
def montar_html():
    condicao = s.get("condicao_ensaio") or {}
    b=condicao.get("barco", s.barco); reg=s.get("ultima_regressao")
    nome=html.escape(str(b.get("nome") or "Não informado"))
    title="Relatório técnico — Prova de inclinação"
    resultado="Sem regressão calculada"
    if reg:
        kg="Não calculável: faltam KM e/ou FSM" if reg["kg_solido_m"] is None else f"{reg['kg_solido_m']:.6f} m"
        resultado=f"GM observado: {reg['gm_observado_m']:.6f} m; KG sólido: {kg}; R²: {reg['r2']:.6f}; n = {reg['n']}."
    def tab(rows):
        if not rows:return "<p>Sem registros.</p>"
        return pd.DataFrame(rows).to_html(index=False,escape=True,classes="tabela")
    return f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>{title}</title>
<style>body{{font:15px/1.5 Arial,sans-serif;max-width:1000px;margin:40px auto;color:#1e293b}}h1,h2{{color:#0e7490}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{border:1px solid #cbd5e1;padding:7px;vertical-align:top}}th{{background:#e2e8f0}}.alerta{{border-left:4px solid #c2410c;padding:12px;background:#fff7ed}}</style>
<h1>{title}</h1><p>Embarcação: <b>{nome}</b></p><p>Gerado em UTC: {datetime.now(timezone.utc).isoformat()}</p>
<div class="alerta">Resultado acadêmico. A prova física, conferência de instrumentos e aprovação da autoridade competente não são substituídas por esta ferramenta. O formato HTML permite impressão em PDF pelo navegador.</div>
<h2>Dados da embarcação</h2>{tab([{"Parâmetro": k, "Valor": v} for k,v in b.items() if not isinstance(v, list)])}
<h2>Tabela hidrostática</h2>{tab(b.get("hidro_tabela"))}
<h2>Curva GZ</h2>{tab(b.get("gz_curva"))}
<h2>Contorno em planta</h2>{tab(b.get("casco_contorno"))}
<h2>Cargas</h2>{tab(condicao.get("cargas",s.cargas))}
<h2>Instrumentos</h2>{tab(condicao.get("pendulos",s.pendulos))}
<h2>Movimentos</h2>{tab(s.movimentos)}
<h2>Leituras</h2>{tab([{k:v for k,v in r.items() if k not in ('pendulos','posicoes_y')} for r in s.leituras])}
<h2>Regressão e resultados</h2><p>{resultado}</p>
<h2>Condições de validade</h2><p>Aproximação metacêntrica para pequenos ângulos. GM estimado por regressão tanθ vs momento inclinado. FSM fornecido para a condição ensaiada. Sem dados completos, os resultados são parciais.</p>
<h2>Limitações</h2><p>Não inclui determinação de hidrostática por malha 3D, certificação de instrumentos, forças reais de vento ou amarras, nem ângulos grandes sem GZ de mesma condição.</p>
<h2>Fontes técnicas</h2><p>IMO 2008 IS Code, resolução MSC.267(85), capítulo 8 e anexo 1; USCG MSC PRG GEN-02; OpenNAOE, cap. 10. Consulte REFERENCIAS.md para links e hipóteses.</p>
</html>'''

report=montar_html()


def make_zip():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("dados_prova_inclinacao.json",json_bytes(pacote))
        z.writestr("relatorio.pdf",pdf)
        z.writestr("comparacao.csv",csv_bytes(pacote["tabela_planejamento"]))
        z.writestr("cargas.csv",csv_bytes(s.cargas))
        z.writestr("movimentos.csv",csv_bytes(s.movimentos))
        z.writestr("leituras.csv",csv_bytes([{k:v for k,v in r.items() if k not in ("pendulos","posicoes_y")} for r in s.leituras]))
        z.writestr("relatorio.html",report.encode("utf-8"))
        from visualization.casco import planta
        from visualization.cargas import perfil
        from visualization.graficos import ajuste,residuos
        from modules.carregamento import calcular
        from modules.hidrostatica import consultar
        import plotly.express as px
        from plotly.offline import get_plotlyjs
        snap=s.get("condicao_ensaio") or {}
        barco=snap.get("barco",s.barco)
        cargas=snap.get("cargas",s.cargas)
        figuras={}
        if cargas or barco.get("casco_contorno"):
            try:
                cond=calcular(barco,cargas)
            except ValueError:
                cond={}
            try:
                h=consultar(barco,cond.get("deslocamento_kg"))
            except ValueError:
                h={}
            figuras["planta"]=planta(barco,cargas,cond)
            figuras["perfil"]=perfil({**barco,"calado_m":h.get("calado_m")},cargas,cond)
        if barco.get("gz_curva"):
            figuras["gz_referencia"]=px.line(sorted(barco["gz_curva"],key=lambda r:r["angulo_graus"]),x="angulo_graus",y="gz_m")
        if pacote["serie_dinamica"]:
            figuras["balanco"]=px.line(pacote["serie_dinamica"],x="tempo_s",y="phi_rad")
        if s.get("ultima_regressao"):
            z.writestr("regressao.json",json_bytes(s.ultima_regressao))
            figuras["regressao"]=ajuste(s.ultima_regressao)
            figuras["residuos"]=residuos(s.ultima_regressao)
        if figuras:
            z.writestr("plotly.min.js",get_plotlyjs())
            for nome,figura in figuras.items():
                z.writestr("grafico_"+nome+".html",figura.to_html(full_html=True,include_plotlyjs="directory"))
    return buf.getvalue()

st.download_button("Baixar relatório técnico em PDF",pdf,file_name="relatorio_prova_inclinacao.pdf",mime="application/pdf",type="primary")
st.divider()
with st.container(border=True):
    st.subheader("Pacote completo")
    st.write("Reúne o relatório, dados da sessão e tabelas CSV. Quando houver regressão, inclui os gráficos de ajuste e resíduos.")
    st.download_button("Baixar pacote completo de resultados (ZIP)",make_zip(),file_name="resultados_prova_inclinacao.zip",mime="application/zip",type="primary")
a, b = st.columns(2)
with a:
    st.caption("Para ler no navegador ou imprimir em PDF")
    st.download_button("Baixar relatório técnico em HTML",report.encode("utf-8"),file_name="relatorio_prova_inclinacao.html",mime="text/html")
with b:
    st.caption("Para reutilizar os dados do ensaio")
    st.download_button("Baixar todos os dados (JSON)",json_bytes(pacote),file_name="dados_prova_inclinacao.json",mime="application/json")

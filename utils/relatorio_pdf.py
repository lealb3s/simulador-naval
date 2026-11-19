"""Relatório A4 em memória. Usa exclusivamente a condição e as leituras recebidas."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Circle, Line, String


def _valor(valor):
    if valor is None:
        return "—"
    return f"{valor:.6g}" if isinstance(valor, float) else str(valor)


def grafico(reg):
    """Plano M × tangente com eixos e ajuste nas unidades originais."""
    g = Drawing(470, 148)
    xs, ys = reg["x"], reg["y"] + reg["y_ajuste"]
    x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
    def px(x): return 62+(x-x0)*365/(x1-x0)
    def py(y): return 32+(y-y0)*96/(y1-y0)
    g.add(Line(62,32,427,32))
    g.add(Line(62,32,62,128))
    for x in (x0,(x0+x1)/2,x1):
        g.add(String(px(x),18,_valor(x),fontSize=8,textAnchor="middle"))
    for y in (y0,(y0+y1)/2,y1):
        g.add(String(54,py(y),_valor(y),fontSize=8,textAnchor="end"))
    g.add(String(260,3,"Momento de massa (kg·m)",fontSize=9,textAnchor="middle"))
    g.add(String(45,137,"Tangente",fontSize=9))
    g.add(Line(px(x0),py(reg["a"]+reg["b"]*x0),px(x1),py(reg["a"]+reg["b"]*x1),strokeColor=colors.HexColor("#227787")))
    for x,y in zip(xs,reg["y"]):
        g.add(Circle(px(x),py(y),2.6,fillColor=colors.HexColor("#be7129"),strokeColor=None))
    return g


def gerar_pdf(dados):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer,pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=20*mm,bottomMargin=18*mm,
                            title="Relatório de prova de inclinação")
    estilos = getSampleStyleSheet()
    tinta=colors.HexColor("#173d4b")
    estilos["Title"].textColor=tinta
    estilos["Heading2"].textColor=tinta
    cel=ParagraphStyle("celula",fontName="Helvetica",fontSize=8,leading=10)
    story=[]
    def texto(txt,estilo="BodyText"):
        story.append(Paragraph(escape(str(txt)),estilos[estilo]))
    def tabela(titulos,linhas):
        if not linhas:
            texto("Sem registros nesta exportação.")
            return
        matriz=[[Paragraph(escape(_valor(v)),cel) for v in row] for row in [titulos,*linhas]]
        obj=Table(matriz,repeatRows=1,hAlign="LEFT",colWidths=[doc.width/len(titulos)]*len(titulos))
        obj.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#c6e1e4")),
                                 ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f1f6f7")])]))
        story.extend([obj,Spacer(1,6)])
    snap=dados.get("condicao_ensaio") or {}
    barco=snap.get("barco",dados["barco"])
    reg=dados.get("ultima_regressao") or {}
    params=dados.get("param_regressao") or snap
    texto("Prova de inclinação","Title")
    texto(barco.get("nome","Embarcação"),"Heading2")
    fontes=sorted({str(r.get("fonte","origem não informada")) for r in dados["leituras"]})
    texto("Origem das leituras · "+(", ".join(fontes) or "Sem leituras"))
    texto("Condição e instrumentos","Heading2")
    tabela(["Deslocamento (kg)","KM (m)","FSM total (kg·m)","Leituras"],[[params.get("delta"),params.get("km"),params.get("fsm"),len(dados["leituras"])]])
    tabela(["Instrumento","Comprimento efetivo (m)"],[[p["id"],p["comprimento_m"]] for p in snap.get("pendulos",dados["pendulos"])])
    texto("Resultado experimental","Heading2")
    if reg:
        tabela(["GM observado (m)","KG sólido (m)","R²","n","u(GM) do ajuste (m)"],[[reg[k] for k in ("gm_observado_m","kg_solido_m","r2","n","u_gm_ajuste_m")]])
        texto(f"tan(ângulo) = {reg['a']:.6g} + ({reg['b']:.6g}) M. M em kg·m. "+reg["avaliacao"])
        texto("A incerteza indicada considera a dispersão do ajuste com deslocamento e momentos fixos. Erros de calibração exigem avaliação independente.")
        if snap.get("gm_ref") is not None:
            texto(f"Referência da simulação congelada · GM efetivo {snap['gm_ref']:.5g} m e KG sólido {snap['kg_ref']:.5g} m.")
        story.append(grafico(reg))
    else:
        texto("Relatório parcial. O ajuste experimental ainda não foi calculado.")
    texto("Cargas na condição de referência","Heading2")
    tabela(["Carga","Categoria","Massa (kg)","X (m)","Y (m)","Z (m)"],[[c[k] for k in ("nome","categoria","massa_kg","x_m","y_m","z_m")] for c in snap.get("cargas",dados["cargas"])])
    texto("Medições","Heading2")
    tabela(["Nº","Momento (kg·m)","Tangente","Banda (°)","Em equilíbrio"],[[r.get("numero",i),r.get("momento_kgm"),r.get("tangente"),r.get("angulo_graus"),"Sim" if r.get("estavel") else "Não"] for i,r in enumerate(dados["leituras"],1)])
    texto("Comparação de configurações","Heading2")
    tabela(["Opção","Massa (kg)","Curso (m)¹","Banda (°)","Divisão angular (°)","Viabilidade"],[[r.get(k) for k in ("Configuração","Massa total (kg)","Distância (m)","Inclinação prevista (°)","Resolução angular (°)","Viabilidade")] for r in dados.get("tabela_planejamento",[])])
    texto("¹ Módulo do curso. O sinal da banda indica o bordo.")
    texto("Método e limites","Heading2")
    texto("GM = 1/(deslocamento × inclinação da reta). KG = KM − GM − FSM/deslocamento. Condição de massa constante e pequenos ângulos. O KG refere-se à condição ensaiada. A hidrostática, a superfície livre e a convenção transversal devem corresponder a essa condição.")
    texto("Fontes · IMO MSC.267(85), parte B, cap. 8 e anexo 1. USCG GEN-02 (2020). OpenNAOE, Hydrostatics and Stability, cap. 10. Equações e referências completas em REFERENCIAS.md.")
    def rodape(canvas,doc):
        canvas.setFillColor(tinta)
        canvas.setFont("Helvetica",8)
        canvas.drawString(18*mm,10*mm,"ENGENHARIA NAVAL   /   RELATÓRIO ACADÊMICO")
        canvas.drawRightString(192*mm,10*mm,str(doc.page))
    doc.build(story,onFirstPage=rodape,onLaterPages=rodape)
    return buffer.getvalue()

"""Testes de regressão pelo ponto de entrada do aplicativo."""
import io
import json
import zipfile
import streamlit as st
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from utils.navegacao import ARQUIVOS, ETAPAS

ROOT = Path(__file__).resolve().parents[1]


def abrir(at, etapa):
    at.switch_page(ARQUIVOS[etapa]).run()
    assert not at.exception


def campo(widgets, rotulo):
    return next(w for w in widgets if w.label == rotulo)


def clicar(at, rotulo):
    campo(at.button, rotulo).click().run()
    assert not at.exception
    assert not at.error, [erro.value for erro in at.error]


def test_fluxo_manual_e_ensaio_dinamico(monkeypatch):
    exportacoes = {}
    baixar = st.download_button
    def guardar(rotulo, conteudo, **kwargs):
        exportacoes[kwargs["file_name"]] = conteudo
        return baixar(rotulo, conteudo, **kwargs)
    monkeypatch.setattr(st, "download_button", guardar)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    for etapa, *_ in ETAPAS:
        abrir(at, etapa)
        assert len(at.page_link) >= 2
    abrir(at, "embarcacao")
    dados = {
        "massa_base_kg":"90", "base_x_m":"1", "base_y_m":"0", "base_z_m":"0,5",
        "L_m":"2", "B_m":"1", "D_m":"1", "fsm_kgm":"0",
        "deslocamento_referencia_kg":"100", "km_m":"1,5",
    }
    for nome, valor in dados.items():
        at.text_input(key=f"barco_0_{nome}").set_value(valor)
    clicar(at, "Salvar dados manuais")
    abrir(at, "cargas")
    for rotulo, valor in [("Nome","Peso A"), ("Massa (kg)","10"), ("X (m)","1"), ("Y (m)","0"), ("Z (m)","0,5")]:
        campo(at.text_input, rotulo).set_value(valor)
    clicar(at, "Adicionar carga")
    clicar(at, "Aplicar alterações na tabela")
    abrir(at, "pendulos")
    campo(at.number_input, "Quantidade de pêndulos").set_value(3).run()
    for i in range(3):
        at.text_input(key=f"plen_{i}").set_value("0,85")
    clicar(at, "Validar e salvar instrumentos")
    abrir(at, "condicoes")
    campo(at.text_input, "Limite angular do ensaio (°)").set_value("4")
    clicar(at, "Salvar condições do ensaio")
    abrir(at, "ensaio")
    clicar(at, "Iniciar prova e congelar condição de carregamento")
    for posicao in [0, -0.3, 0.3]:
        campo(at.number_input, "Nova coordenada Y (m)").set_value(posicao)
        clicar(at, "Movimentar o peso")
        clicar(at, "Registrar condição experimental simulada")
    campo(at.checkbox, "Habilitar modelo dinâmico linear de rolamento").check().run()
    for w, v in zip(at.text_input, ["3","5","0,01","0,01"]):
        w.set_value(v)
    clicar(at, "Aplicar parâmetros dinâmicos")
    clicar(at, "Avançar dinâmica")
    assert at.session_state["dinamica"]["tempo_s"] == pytest.approx(1)
    clicar(at, "Encerrar prova (manter leituras)")
    assert at.title[0].value == "Processamento de GM e KG"
    abrir(at, "processamento")
    clicar(at, "Calcular regressão")
    r = at.session_state["ultima_regressao"]
    assert r["gm_observado_m"] == pytest.approx(1)
    assert r["kg_solido_m"] == pytest.approx(.5)
    abrir(at, "relatorio")
    with zipfile.ZipFile(io.BytesIO(exportacoes["resultados_prova_inclinacao.zip"])) as pacote:
        assert pacote.testzip() is None
        assert "plotly.min.js" in pacote.namelist()
        assert json.loads(pacote.read("regressao.json"))["n"] == 3
        assert json.loads(pacote.read("dados_prova_inclinacao.json"))["condicao_ensaio"]["delta"] == 100


@pytest.mark.skipif(not hasattr(AppTest, "file_uploader"), reason="Streamlit instalado sem suporte a upload no AppTest")
def test_importar_planilha_multiaba_sem_reenvio():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    abrir(at, "embarcacao")
    arq = io.BytesIO()
    with pd.ExcelWriter(arq, engine="openpyxl") as writer:
        pd.DataFrame({"Nota":["Revisar"]}).to_excel(writer, sheet_name="Resumo", index=False)
        pd.DataFrame({"campo":["nome","B"],"valor":["Casco teste",2]}).to_excel(writer, sheet_name="Ficha", index=False)
        pd.DataFrame({"nome":["Lastro"],"massa [kg]":["12,5"],"x_m":[1],"y_m":[0],"z_m":[.2]}).to_excel(writer,sheet_name="Pesos", index=False, startrow=2)
    at.file_uploader[0].upload("Ensaio.xlsx", arq.getvalue()).run()
    campo(at.selectbox, "Aba do Excel").set_value("Pesos").run()
    clicar(at, "Abrir esta tabela em Carregamento")
    assert at.title[0].value == "Carregamento"
    abrir(at, "cargas")
    assert campo(at.selectbox, "Aba do Excel").value == "Pesos"
    assert campo(at.number_input, "Linha do cabeçalho").value == 3
    campo(at.selectbox, "Massa na planilha *").set_value("kg")
    campo(at.selectbox, "Posições e dimensões na planilha *").set_value("m")
    clicar(at, "Validar e substituir cargas importadas")
    assert at.session_state["cargas"][0]["massa_kg"] == pytest.approx(12.5)


def test_hidro_csv_e_ficha_json():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    abrir(at, "embarcacao")
    at.file_uploader[0].upload("hidro.csv", b"Delta (deslocamento) [t];T moldado [m];KM_t [m]\n1,5;0,8;1,2\n").run()
    clicar(at, "Validar e importar")
    barco = at.session_state["barco"]
    assert barco["hidro_tabela"][0]["deslocamento_kg"] == pytest.approx(1500)
    at.file_uploader[0].upload("ficha.json", b'{"nome":"Barco de teste","massa_base_kg":1300}').run()
    clicar(at, "Validar e importar")
    assert at.session_state["barco"]["massa_base_kg"] == 1300
    assert at.session_state["barco"]["hidro_tabela"] == barco["hidro_tabela"]


def test_entrada_manual_vazia_depois_do_pontao():
    at=AppTest.from_file(str(ROOT/"app.py"),default_timeout=20).run()
    clicar(at,"Carregar exemplo fictício")
    abrir(at,"embarcacao")
    assert not at.text_input
    clicar(at,"Abrir entrada manual")
    assert at.session_state["barco"]["nome"]==""
    for campo_nome in ("L_m","B_m","D_m","massa_base_kg","km_m","fsm_kgm"):
        assert at.text_input(key=f"barco_0_{campo_nome}").value==""
    assert campo(at.text_input,"Identificação").value==""
    assert at.session_state["cargas"]==[]
    assert at.session_state["erros"]=={}
    assert all(p["comprimento_m"] is None for p in at.session_state["pendulos"])
    abrir(at,"pendulos")
    assert campo(at.number_input,"Banda de projeto (°)").value is None
    abrir(at,"planejamento")
    assert campo(at.number_input,"Curso disponível por peso (m)").value is None


def test_alternar_projetos_preserva_apenas_os_dados_do_projeto_ativo():
    at=AppTest.from_file(str(ROOT/"app.py"),default_timeout=20).run()
    clicar(at,"Abrir entrada manual")
    abrir(at,"embarcacao")
    campo(at.text_input,"Identificação").set_value("Embarcação da Beatriz")
    at.text_input(key="barco_0_L_m").set_value("19,19")
    clicar(at,"Salvar dados manuais")
    abrir(at,"cargas")
    for rotulo,valor in [("Nome","Caixa própria"),("Massa (kg)","25"),("X (m)","1"),("Y (m)","0"),("Z (m)","0,8")]:
        campo(at.text_input,rotulo).set_value(valor)
    clicar(at,"Adicionar carga")
    at.switch_page("inicio.py").run()
    clicar(at,"Carregar exemplo fictício")
    assert at.session_state["barco"]["L_m"]==8
    assert len(at.session_state["cargas"])==3
    clicar(at,"Usar minha embarcação")
    abrir(at,"embarcacao")
    assert campo(at.text_input,"Identificação").value=="Embarcação da Beatriz"
    assert float(campo(at.text_input,"Comprimento (m)").value)==19.19
    assert campo(at.text_input,"Boca (m)").value==""
    assert [c["nome"] for c in at.session_state["cargas"]]==["Caixa própria"]
    assert not at.session_state["leituras"]
    assert at.session_state["pendulos"][0]["comprimento_m"] is None


def test_importacao_total_nao_vira_carga():
    at=AppTest.from_file(str(ROOT/"app.py"),default_timeout=20).run()
    abrir(at,"cargas")
    dados=b"nome,massa_kg,x_m,z_m\nCaixa,110,4,1\nBomba,50,5,0.5\nTOTAL,160,,\n"
    at.file_uploader[0].upload("pesos.csv",dados).run()
    assert campo(at.checkbox,"Excluir linhas de total ou subtotal (1)").value
    clicar(at,"Validar e substituir cargas importadas")
    cargas=at.session_state["cargas"]
    assert len(cargas)==2 and sum(c["massa_kg"] for c in cargas)==160
    assert all(c["y_m"]==0 for c in cargas)

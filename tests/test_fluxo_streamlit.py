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

"""Casos da literatura, balanços manuais e fluxo de nove leituras pelo app."""
from math import degrees, atan
import io
import json
import zipfile

import numpy as np
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from modules.carregamento import base_da_condicao, calcular
from modules.criterios import banda_inicial
from modules.erros_experimentais import momento_externo, perturbar
from modules.estabilidade import avaliar
from modules.hidrostatica import consultar
from modules.regressao import processar
from modules.prova_inclinacao import serie_transitoria, estabilizado
from utils.exemplo import exemplo
from utils.importacao import verificar_unidade_declarada
from utils.navegacao import ARQUIVOS
from visualization.inclinacao import secao
from pathlib import Path

RAIZ=Path(__file__).resolve().parents[1]


def test_exemplo_derrett_barrass_p289():
    # Ex. 2, 6ª ed., p.289. O autor pede Δ; reusamos a solução pelo sentido inverso.
    delta = 8_000_000
    momentos=[-120_000,0,120_000]
    leituras=[{"momento_kgm":m,"tangente":y,"estavel":True} for m,y in zip(momentos,[-.25/10,0,.25/10])]
    assert processar(leituras,delta)["gm_observado_m"]==pytest.approx(.6)


def test_pontao_e_movimento_lateral():
    b,c=exemplo()
    cond=calcular(b,c)
    assert cond["deslocamento_kg"]==12000
    assert (cond["lcg_m"],cond["tcg_m"],cond["kg_m"])==(4,0,.75)
    hidro=consultar(b,12000)
    assert hidro["calado_m"]==.5 and hidro["km_m"]==1.75
    assert avaliar(b,cond,hidro)["gm_efetivo_m"]==1
    c[0]["y_m"]=1.25
    assert banda_inicial(calcular(b,c)["tcg_m"],1)==pytest.approx(degrees(atan(312.5/12000)))
    assert banda_inicial(.2,1) is None
    grafico=secao({**b,"calado_m":.5},2,.75,.25,1.75)
    assert grafico.data[0].y[1] < grafico.data[0].y[0]


def test_base_global_sem_dupla_contagem():
    b,c=exemplo()
    cond=calcular(b,c)
    base=base_da_condicao(12000,cond,c)
    assert base["massa_base_kg"]==11000 and base["base_z_m"]==.75
    assert calcular({**b,**base},c)["kg_m"]==.75
    with pytest.raises(ValueError):
        base_da_condicao(200,cond,c)


@pytest.mark.parametrize("origem,unidade,grandeza",[
    ("Deslocamento [kN]","kg","deslocamento_kg"),("KM_l [m]","m","km_m"),
    ("MCT [t·m/cm]","kg·m/m","mtc_kgm_por_m")])
def test_unidades_e_eixos_incompativeis(origem,unidade,grandeza):
    with pytest.raises(ValueError):
        verificar_unidade_declarada(origem,unidade,grandeza)


def test_erros_e_dinamica():
    cfg={"sigma_vento_Nm":20,"interferencia_Nm":3,"vies_comprimento_pct":10}
    assert momento_externo(cfg,2)==momento_externo(cfg,2)
    assert momento_externo(cfg,2)!=momento_externo(cfg,3)
    _,leituras=perturbar(300,[{"id":"P","comprimento_m":2}],2,cfg,np.random.default_rng(1))
    assert leituras[0]["comprimento_m"]==pytest.approx(2.2)
    assert leituras[0]["angulo_medido_graus"]<2
    estado={"tempo_s":0,"phi_rad":0,"omega_rad_s":0}
    conf={"I":10000,"c":8000}
    serie=serie_transitoria(estado,312.5,12000,1,conf,30,151)
    assert not estabilizado(serie[0],312.5,12000,1,.01,.01)
    assert estabilizado(serie[-1],312.5,12000,1,.01,.01)
    assert max(r["phi_rad"] for r in serie)>312.5/12000


def test_nove_leituras_e_pdf(monkeypatch):
    arquivos={}
    original=st.download_button
    def guardar(label,data,**kw):
        arquivos[kw["file_name"]]=data
        return original(label,data,**kw)
    monkeypatch.setattr(st,"download_button",guardar)
    at=AppTest.from_file(str(RAIZ/"app.py"),default_timeout=20).run()
    def botao(nome):
        next(w for w in at.button if w.label==nome).click().run()
        assert not at.exception and not at.error
    def abrir(chave):
        at.switch_page(ARQUIVOS[chave]).run()
        assert not at.exception
    botao("Carregar exemplo fictício")
    abrir("planejamento")
    botao("Comparar configurações")
    assert len(at.session_state["tabela_planejamento"])==3
    abrir("ensaio")
    botao("Iniciar prova e congelar condição de carregamento")
    botao("Registrar condição experimental simulada")
    for n,y in [(0,1.25),(1,1.25),(0,0),(1,0),(0,-1.25),(1,-1.25),(0,0),(1,0)]:
        escolha=next(w for w in at.selectbox if w.label=="Peso a movimentar")
        escolha.set_value(["Peso de vante","Peso de ré"][n]).run()
        next(w for w in at.number_input if w.label=="Nova coordenada Y (m)").set_value(y)
        botao("Movimentar o peso")
        botao("Registrar condição experimental simulada")
    botao("Encerrar prova (manter leituras)")
    abrir("processamento")
    botao("Calcular regressão")
    r=at.session_state["ultima_regressao"]
    assert r["n"]==9 and r["gm_observado_m"]==pytest.approx(1)
    assert r["kg_solido_m"]==pytest.approx(.75)
    assert r["x"]==[0,312.5,625,312.5,0,-312.5,-625,-312.5,0]
    abrir("relatorio")
    with zipfile.ZipFile(io.BytesIO(arquivos["resultados_prova_inclinacao.zip"])) as z:
        assert z.read("relatorio.pdf").startswith(b"%PDF-")
        assert z.read("relatorio.pdf").rstrip().endswith(b"%%EOF")
        assert len(json.loads(z.read("dados_prova_inclinacao.json"))["tabela_planejamento"])==3
        assert "comparacao.csv" in z.namelist()


def test_condicao_global_arquivo_e_unidades():
    at=AppTest.from_file(str(RAIZ/"app.py"),default_timeout=20).run()
    at.switch_page(ARQUIVOS["embarcacao"]).run()
    at.file_uploader[0].upload("cond.csv",b"deslocamento [t];lcg [m];tcg [m];kg [m]\n12;4;0;0,75\n").run()
    next(w for w in at.button if w.label=="Importar condição e calcular massa base").click().run()
    assert not at.exception and not at.error
    assert at.session_state["barco"]["massa_base_kg"]==12000
    assert at.session_state["barco"]["base_z_m"]==.75


def test_rejeita_angulo_fora_do_dominio():
    linhas=[{"momento_kgm":x,"tangente":x/100,"estavel":True} for x in (-9,0,9)]
    with pytest.raises(ValueError,match="domínio"):
        processar(linhas,1000)


def test_opcional_interpolado_apenas_entre_vizinhos():
    barco={"hidro_tabela":[{"deslocamento_kg":m,"calado_m":t,"km_m":1.4,"kb_m":k} for m,t,k in
                           [(1000,.5,.25),(2000,1,.5),(3000,1.5,None)]]}
    assert consultar(barco,1500)["kb_m"]==pytest.approx(.375)
    assert consultar(barco,2500)["kb_m"] is None


def test_evento_drag_atualiza_formulario_e_desfazer(monkeypatch):
    import components.cargo_drag
    resposta={}
    monkeypatch.setattr(components.cargo_drag,"drag",lambda *a,**kw: resposta.copy())
    at=AppTest.from_file(str(RAIZ/"app.py"),default_timeout=20).run()
    next(w for w in at.button if w.label=="Carregar exemplo fictício").click().run()
    at.switch_page(ARQUIVOS["movimentacao"]).run()
    resposta.update(id="P2",x_m=3.,y_m=1.,nonce=22)
    at.run()
    assert not at.exception
    assert at.selectbox(key="carga_escolhida").value=="P2"
    assert next(w.value for w in at.number_input if w.label=="Y (m)")==1.
    assert calcular(at.session_state["barco"],at.session_state["cargas"])["deslocamento_kg"]==12000
    next(w for w in at.button if w.label=="Desfazer").click().run()
    assert next(c for c in at.session_state["cargas"] if c["id"]=="P2")["y_m"]==0.


def test_bloqueio_de_leitura_dinamica_pela_interface():
    at=AppTest.from_file(str(RAIZ/"app.py"),default_timeout=20).run()
    def clicar(label):
        next(x for x in at.button if x.label==label).click().run()
        assert not at.exception and not at.error
    clicar("Carregar exemplo fictício")
    at.switch_page(ARQUIVOS["ensaio"]).run()
    clicar("Iniciar prova e congelar condição de carregamento")
    next(w for w in at.checkbox if "Habilitar modelo" in w.label).check().run()
    for w,v in zip(at.text_input,["10000","8000","0,01","0,01"]):
        w.set_value(v)
    clicar("Aplicar parâmetros dinâmicos")
    next(w for w in at.number_input if w.label=="Nova coordenada Y (m)").set_value(1.25)
    clicar("Movimentar o peso")
    assert next(w for w in at.button if w.label=="Registrar condição experimental simulada").disabled
    next(w for w in at.number_input if "Avançar tempo" in w.label).set_value(30.)
    clicar("Avançar dinâmica")
    assert not next(w for w in at.button if w.label=="Registrar condição experimental simulada").disabled
    clicar("Registrar condição experimental simulada")
    assert at.session_state["leituras"][-1]["fonte"]=="simulacao_dinamica"

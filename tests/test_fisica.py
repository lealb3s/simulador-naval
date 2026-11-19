"""Casos sintéticos identificados como testes e exemplo da literatura OpenNAOE cap.10.
Não são dados reais para usar em operação de embarcação específica.
"""
import copy
from math import atan, degrees
import numpy as np
import pytest
from modules.carregamento import calcular,momento_deslocamento
from modules.hidrostatica import consultar,superficie_livre,trim_estatico
from modules.estabilidade import avaliar,gz_adaptada
from modules.pendulos import angulo,deflexao,resolucao_angular
from modules.movimentacao_pesos import momento_inclinante,angulo_previsto,comparar
from modules.prova_inclinacao import equilibrio_angulo,avancar_dinamica,estabilizado
from modules.regressao import processar,sensibilidade
from modules.erros_experimentais import perturbar
from modules.validacao import verificar_carga, ordenar_hidro_tabela

@pytest.fixture
def barco():
    return {"nome":"ENSAIO SINTÉTICO — NÃO REAL","massa_base_kg":1000,"base_x_m":3,"base_y_m":0,"base_z_m":1,
            "L_m":10,"B_m":4,"D_m":3,"deslocamento_referencia_kg":1100,"calado_m":1.25,"km_m":2.5,
            "kb_m":0.6,"lcb_m":3.1,"lcf_m":3.5,"mtc_kgm_por_m":10000,"fsm_kgm":110,
            "hidro_tabela":[],"gz_curva":[],"casco_contorno":[]}

@pytest.fixture
def carga():
    return {"id":"A","nome":"peso","categoria":"lastro","massa_kg":100,"x_m":5,"y_m":0,"z_m":0.5,
            "comp_m":0.5,"larg_m":0.3,"alt_m":0.5}


def test_balanco_massa_cg(barco,carga):
    r=calcular(barco,[carga]);assert r["deslocamento_kg"]==1100
    assert r["lcg_m"]==pytest.approx((3000+500)/1100)
    assert r["kg_m"]==pytest.approx((1000+50)/1100)
    assert r["tcg_m"]==0
    assert r["momento_z_m"]==1050


def test_movimentacao_conserva_deslocamento_e_muda_tcg(barco,carga):
    a=calcular(barco,[carga]);b=copy.deepcopy(carga);b["y_m"]=1.0
    depois=calcular(barco,[b]);assert depois["deslocamento_kg"]==a["deslocamento_kg"]
    assert depois["tcg_m"]==pytest.approx(100/1100)
    assert momento_deslocamento([carga],[b])==100


def test_elevacao_muda_kg_e_longitudinal_muda_lcg(barco,carga):
    a=calcular(barco,[carga]);z=copy.deepcopy(carga);z["z_m"]=1.5
    x=copy.deepcopy(carga);x["x_m"]=6
    assert calcular(barco,[z])["kg_m"]-a["kg_m"]==pytest.approx(100/1100)
    assert calcular(barco,[x])["lcg_m"]-a["lcg_m"]==pytest.approx(100/1100)


def test_adicionar_retirar_carga_muda_deslocamento(barco,carga):
    a=calcular(barco,[])["deslocamento_kg"]
    assert calcular(barco,[carga])["deslocamento_kg"]==a+100
    assert calcular(barco,[])["deslocamento_kg"]==a


def test_hidro_sem_extrapolacao(barco):
    barco["hidro_tabela"]=[{"deslocamento_kg":1000,"calado_m":1.0,"km_m":2.0},
                           {"deslocamento_kg":2000,"calado_m":2.0,"km_m":3.0}]
    mid=consultar(barco,1500)
    assert mid["calado_m"]==1.5 and mid["km_m"]==2.5
    with pytest.raises(ValueError,match="extrapolação proibida"):
        consultar(barco,2100)


def test_hidro_sem_tabela_so_exata(barco):
    assert consultar(barco,1100)["km_m"]==2.5
    with pytest.raises(ValueError,match="Sem tabela"):
        consultar(barco,1200)


def test_gm_e_superficie_livre(barco,carga):
    cond=calcular(barco,[carga]);h=consultar(barco,1100)
    e=avaliar(barco,cond,h)
    assert superficie_livre(barco,1100)==pytest.approx(0.1)
    assert e["gm_efetivo_m"]==pytest.approx(2.5-1050/1100-0.1)
    barco["fsm_kgm"]=None
    assert avaliar(barco,cond,h)["gm_efetivo_m"] is None


def test_trim_somente_se_mct_disponivel(barco,carga):
    cond=calcular(barco,[carga]);h=consultar(barco,1100)
    r=trim_estatico(cond,h)
    assert r["momento_trim_kgm"]==pytest.approx(1100*(cond["lcg_m"]-3.1))
    assert r["variacao_trim_m"]==pytest.approx(r["momento_trim_kgm"]/10000)
    h["mtc_kgm_por_m"]=None
    assert trim_estatico(cond,h)["variacao_trim_m"] is None


def test_angulo_e_pendulo():
    theta=angulo_previsto(120000,2918000,1.25)
    assert theta==pytest.approx(1.884,abs=0.01) # Ex. OpenNAOE 10.2
    L=5.5
    x=deflexao(L,theta)
    assert angulo(L,x)==pytest.approx(theta)
    assert resolucao_angular(5,0.001)<resolucao_angular(2,0.001)


def test_opennaoe_exemplo_10_1():
    """Series 60: resultados publicados com arredondamentos 1.243 m e 6.781 m."""
    delta=2917.8*1000
    moment=(5*12.02+5*11.98)*1000
    tangent=.182/5.5
    gm=moment/(delta*tangent)
    assert gm==pytest.approx(1.243,abs=.002)
    assert 8.024-gm==pytest.approx(6.781,abs=.002)
    assert degrees(atan(tangent))==pytest.approx(1.90,abs=.01)


def test_regressao_exata_e_fsc():
    d, gm, km, fsm=1000,1.5,2.5,100
    points=[{"momento_kgm":x,"tangente":.002+x/(d*gm),"estavel":True} for x in (-40,-30,-20,-10,0,10,20,30,40)]
    fit=processar(points,d,km,fsm)
    assert fit["gm_observado_m"]==pytest.approx(gm,abs=1e-10)
    assert fit["kg_solido_m"]==pytest.approx(.9,abs=1e-10)
    assert fit["r2"]==pytest.approx(1)
    assert fit["a"]==pytest.approx(.002,abs=1e-10)
    assert max(map(abs,fit["residuos"]))<1e-12


def test_regressao_bloqueia_caso_nao_identificavel():
    with pytest.raises(ValueError,match="3 momentos"):
        processar([{"momento_kgm":1,"tangente":.01,"estavel":True} for _ in range(4)],1000)
    with pytest.raises(ValueError,match="3 leituras"):
        processar([{"momento_kgm":1,"tangente":.01,"estavel":True}],1000)


def test_gz_dif_kg_no_mesmo_deslocamento(barco,carga):
    barco["fsm_kgm"]=0
    barco["gz_deslocamento_kg"]=1100
    barco["gz_kg_referencia_m"]=1.0
    barco["gz_curva"]=[{"angulo_graus":30,"gz_m":.3}]
    r=gz_adaptada(barco,calcular(barco,[carga]))
    assert r[0]["gz_m"]==pytest.approx(.3+(1-1050/1100)*.5)
    barco["fsm_kgm"]=110
    with pytest.raises(ValueError,match="FSM=0"):
        gz_adaptada(barco,calcular(barco,[carga]))


def test_dinamica_e_tolerancia():
    # Exemplo sintético: integração ODE deve se aproximar do equilíbrio após amortecimento suficiente.
    end=avancar_dinamica({"phi_rad":0,"omega_rad_s":0,"tempo_s":0},10,1000,1.0,1000,2000,20)
    assert end["phi_rad"]==pytest.approx(.01,abs=.0001)
    assert estabilizado(end,10,1000,1,.05,.05)
    assert not estabilizado({"phi_rad":0,"omega_rad_s":1},10,1000,1,.05,.05)


def test_sensibilidade_linear_independente():
    r=sensibilidade(10,1,1000,5,.1,{"massa_kg":.1,"distancia_m":0,"deslocamento_kg":0,
                                       "comprimento_m":0,"deflexao_m":0})
    assert r["gm_m"]==pytest.approx(.5)
    assert r["incerteza_padrao_m"]==pytest.approx(.005)


def test_vies_aleatorio_zero():
    rng=np.random.default_rng(42)
    e,p=perturbar(10,[{"id":"P1","comprimento_m":3.0},{"id":"P2","comprimento_m":4.0}],1.0,
                   {"vies_massa_pct":10,"vies_dist_pct":0,"desvio_leitura_m":0},rng)
    assert e==pytest.approx(11)
    assert p[0]["deflexao_m"]==pytest.approx(3*np.tan(np.deg2rad(1)))


def test_limite_fisico_de_carga(barco,carga):
    verificar_carga(carga,barco)
    carga["y_m"]=2.01
    with pytest.raises(ValueError,match="boca"):
        verificar_carga(carga,barco)


def test_comparacao_sem_limites_sem_recomendacao():
    conf=[{"massa_kg":10,"distancia_m":1,"quantidade":1,"pendulo_m":2}]
    rows=comparar(conf,1000,1)
    assert rows[0]["Viabilidade"]=="Não comprovada"


def test_hidro_duas_linhas_vazias_nao_gera_erro_de_comparacao():
    assert ordenar_hidro_tabela([{"deslocamento_kg": None, "calado_m": None, "km_m": None},
                                {"deslocamento_kg": None, "calado_m": None, "km_m": None}]) == []


def test_hidro_linha_incompleta_da_mensagem_util():
    with pytest.raises(ValueError, match="linha 2: preencha 'deslocamento_kg'"):
        ordenar_hidro_tabela([{"deslocamento_kg": 100, "calado_m": .4, "km_m": .8},
                             {"deslocamento_kg": None, "calado_m": .5, "km_m": .9}])


def test_hidro_consulta_linha_incompleta_gera_value_error_antes_de_sort(barco):
    barco["hidro_tabela"] = [{"deslocamento_kg": None, "calado_m": .5, "km_m": .9},
                             {"deslocamento_kg": None, "calado_m": .7, "km_m": 1.1}]
    with pytest.raises(ValueError, match="preencha 'deslocamento_kg'"):
        consultar(barco, 1100)


def test_hidro_importado_textual_ordenado_numericamente(barco):
    tabela = [{"deslocamento_kg": "2000", "calado_m": "2", "km_m": "3"},
              {"deslocamento_kg": "1000", "calado_m": "1", "km_m": "2"}]
    barco["hidro_tabela"] = tabela
    r = consultar(barco, 1500)
    assert r["calado_m"] == pytest.approx(1.5)
    assert r["km_m"] == pytest.approx(2.5)


def test_hidro_duplicados_rejeitados_apos_validacao():
    with pytest.raises(ValueError, match="estritamente crescentes"):
        ordenar_hidro_tabela([{"deslocamento_kg": 100, "calado_m": 1, "km_m": 2},
                             {"deslocamento_kg": 100, "calado_m": 1.1, "km_m": 2.1}])


def test_arquivo_tabela_cabecalhos_desconhecidos_bloqueado():
    from utils.dados import tabela_para_lista, COLUNAS_HIDRO
    with pytest.raises(ValueError,match="Colunas não reconhecidas"):
        tabela_para_lista([{"Deslocamento (t)":2, "Calado (m)":1, "KM (m)":2}],COLUNAS_HIDRO)


def test_importacao_csv_portugues_preserva_virgula_quando_explicitamente_escolhida():
    from utils.dados import ler
    from types import SimpleNamespace
    arquivo=SimpleNamespace(name="hidro.csv", getvalue=lambda: b"deslocamento_kg;calado_m;km_m\\n1000;1,25;2,50\\n2000;1,75;3,00\\n".replace(b"\\n",b"\n"))
    resultado=ler(arquivo,"hidro",decimal_virgula=True)
    # A leitura preserva os textos originais; a conversão numérica ocorre
    # apenas após o mapeamento e confirmação explícita da convenção decimal.
    from utils.dados import tabela_para_lista
    converted=tabela_para_lista(resultado,['deslocamento_kg','calado_m','km_m'],decimal_virgula=True)
    assert converted[0]['calado_m'] == pytest.approx(1.25)
    assert converted[1]["km_m"] == pytest.approx(3)


def test_planilha_hydrostatic_table_mapeamento_cabecalhos_exatos():
    """Cabeçalhos do arquivo real enviado, sem depender do Excel no repositório."""
    from utils.mapeamento import sugestao_coluna
    origem = ["T moldado [m]", "T extremo [m]", "Delta (deslocamento) [t]",
              "LCB [m]", "LCF [m]", "KB = VCB [m]", "KM_t [m]",
              "KM_l [m]", "KG (informado) [m]", "GM_t [m]"]
    esperados = {"deslocamento_kg": "Delta (deslocamento) [t]",
                 "calado_m": "T moldado [m]", "km_m": "KM_t [m]",
                 "kb_m": "KB = VCB [m]", "lcb_m": "LCB [m]", "lcf_m": "LCF [m]"}
    for campo, nome in esperados.items():
        assert sugestao_coluna('hidro', campo, origem) == nome
    assert sugestao_coluna('hidro', 'mtc_kgm_por_m', origem) is None
    assert sugestao_coluna('hidro', 'km_m', ["KM_l [m]"]) is None


def test_arquivo_hidrostatic_table_conversao_e_consulta_com_opcionais_vazios():
    from utils.dados import tabela_para_lista, COLUNAS_HIDRO
    linhas=[{"deslocamento_kg":1.116125288,"calado_m":0.2,
            "km_m":0.6804128904878872,"kb_m":0.1273151036546834,
            "lcb_m":10.27565943558301,"lcf_m":10.08618420007549,
            "mtc_kgm_por_m":None},
            {"deslocamento_kg":96.60879276875,"calado_m":1.8,
            "km_m":2.905513875762222,"kb_m":1.16125094313057,
            "lcb_m":8.080366532535274,"lcf_m":8.377471920841227,
            "mtc_kgm_por_m":None}]
    importados=tabela_para_lista(linhas,COLUNAS_HIDRO)
    for r in importados:r['deslocamento_kg']*=1000
    bar={'hidro_tabela':ordenar_hidro_tabela(importados)}
    assert consultar(bar,96608.79276875)['km_m']==pytest.approx(2.905513875762222)
    assert consultar(bar,96608.79276875)['mtc_kgm_por_m'] is None

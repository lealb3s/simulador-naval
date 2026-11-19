"""Reconhecimento de esquemas de importação sem inferência de unidades."""
from types import SimpleNamespace
import pytest

from utils.mapeamento import identificar_tipo_tabela, sugestao_coluna
from utils.dados import ler, tabela_para_lista, COLUNAS_HIDRO
from modules.validacao import ordenar_hidro_tabela


def test_planilha1_reconhecida_hidro():
    nomes = ["T moldado [m]", "T extremo [m]", "Delta (deslocamento) [t]",
             "LCB [m]", "LCF [m]", "KB = VCB [m]", "BM_t [m]", "KM_t [m]",
             "BM_l [m]", "KM_l [m]", "KG (informado) [m]", "GM_t [m]"]
    assert identificar_tipo_tabela(nomes) == "hidro"
    assert sugestao_coluna("hidro", "km_m", nomes) == "KM_t [m]"
    assert sugestao_coluna("hidro", "deslocamento_kg", nomes) == "Delta (deslocamento) [t]"
    assert sugestao_coluna("hidro", "calado_m", nomes) == "T moldado [m]"


def test_ficha_barco_nao_confundida_com_hidrost(self=None):
    assert identificar_tipo_tabela(["campo", "valor"]) == "barco"
    assert identificar_tipo_tabela(["nome", "massa_base_kg", "L_m"]) is None
    assert identificar_tipo_tabela(["deslocamento_kg", "calado_m"]) is None


def test_reconhece_outros_tipos_global():
    assert identificar_tipo_tabela(["angulo_graus", "gz_m"]) == "gz"
    assert identificar_tipo_tabela(["x_m", "y_m"]) == "casco"


def test_falha_controlada_se_escolher_barco_com_multiplas_linhas():
    texto = ("T moldado [m],Delta (deslocamento) [t],KM_t [m]\n"
             "0.2,1.116125288,0.6804128904878872\n"
             "0.4,4.38122472975,1.450772979833403\n")
    arquivo = SimpleNamespace(name="tabela hidrostática.csv", getvalue=lambda: texto.encode())
    assert identificar_tipo_tabela(ler(arquivo, "hidro")[0].keys()) == "hidro"
    with pytest.raises(ValueError,match="Grandeza/Valor"):
        ler(arquivo, "barco")


def test_mapeamento_mantem_unidade_explicita():
    texto = ("T moldado [m],Delta (deslocamento) [t],KM_t [m],KB = VCB [m],LCB [m],LCF [m]\n"
             "0.2,1.116125288,0.6804128904878872,0.1273151036546834,10.27565943558301,10.08618420007549\n"
             "0.4,4.38122472975,1.450772979833403,0.2666158581520242,9.644010433259407,8.900223751149012\n")
    arquivo = SimpleNamespace(name="hidro.csv",getvalue=lambda: texto.encode())
    rows = ler(arquivo,"hidro")
    mapeamento={c:sugestao_coluna("hidro",c,rows[0].keys()) for c in COLUNAS_HIDRO}
    prepared=tabela_para_lista([{key:r.get(source) if source else None for key,source in mapeamento.items()}
                                for r in rows],COLUNAS_HIDRO)
    for r in prepared:
        r["deslocamento_kg"]*=1000  # confirmado pelo usuário no app
    validated=ordenar_hidro_tabela(prepared)
    assert validated[0]["deslocamento_kg"]==pytest.approx(1116.125288)
    assert validated[0]["km_m"]==pytest.approx(0.6804128904878872)
    assert validated[0]["mtc_kgm_por_m"] is None

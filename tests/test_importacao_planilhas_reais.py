"""Leitura de planilhas com várias abas e cabeçalhos em português."""
from types import SimpleNamespace
import pytest
from utils.importacao import ler_tabela, inspecionar_abas, ler_bruto, escolher_cabecalho, aliases_barco
from utils.mapeamento import sugestao_coluna, identificar_tipo_tabela
from utils.dados import ler, tabela_para_lista, COLUNAS_HIDRO, numero_localizado
from modules.validacao import ordenar_hidro_tabela

@pytest.fixture
def planilha(tmp_path):
    import pandas as pd
    caminho = tmp_path / "ensaio.xlsx"
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        pd.DataFrame({"Notas":["Ensaio de teste"]}).to_excel(writer, sheet_name="Resumo", index=False)
        pd.DataFrame({"Delta (deslocamento) [t]":[1.25, 2.5], "T moldado [m]":[.2,.3],
                      "KM_t [m]":[.8,1.2]}).to_excel(writer, sheet_name="Hidrostática", index=False, startrow=2)
        pd.DataFrame({"Grandeza":["nome","B","D","Td","LPP"],
                      "Valor":["Modelo",5.3,2.7,1.8,18]}).to_excel(writer, sheet_name="Ficha", index=False)
    return SimpleNamespace(name=caminho.name, getvalue=caminho.read_bytes)


def test_multiaba_classificacao_e_ficha(planilha):
    tipos = {r["aba"]:r["tipo"] for r in inspecionar_abas(planilha)}
    assert tipos == {"Resumo":None, "Hidrostática":"hidro", "Ficha":"barco"}
    dados = ler(planilha,"barco",aba="Ficha")
    assert dados["nome"] == "Modelo"
    assert dados["B_m"] == pytest.approx(5.3)
    assert dados["D_m"] == pytest.approx(2.7)
    assert dados["calado_m"] == pytest.approx(1.8)
    assert "L_m" not in dados


def test_multiaba_hidrostatica(planilha):
    rows = ler(planilha, "hidro", aba="Hidrostática")
    campos = {c:sugestao_coluna("hidro",c,rows[0]) for c in COLUNAS_HIDRO}
    registros = tabela_para_lista([{c:row.get(origem) for c,origem in campos.items()} for row in rows], COLUNAS_HIDRO)
    for r in registros:
        r["deslocamento_kg"] *= 1000
    registros = ordenar_hidro_tabela(registros)
    assert [r["deslocamento_kg"] for r in registros] == [1250, 2500]
    assert registros[-1]["km_m"] == pytest.approx(1.2)


def test_cabecalho_deslocado_e_linhas_vazias_csv():
    sample=b'Nota;nao importar\n\ndeslocamento_kg;calado_m;km_m\n1000;1,0;2,0\n\n2000;2,0;3,0\n'
    file=SimpleNamespace(name='dados.csv',getvalue=lambda:sample)
    header,categoria=escolher_cabecalho(ler_bruto(file))
    assert categoria=='hidro'
    assert header==2
    rows=ler_tabela(file)
    data=tabela_para_lista(rows,['deslocamento_kg','calado_m','km_m'],decimal_virgula=True)
    assert len(data)==2
    assert data[0]['calado_m']==pytest.approx(1.0)
    assert data[1]['km_m']==pytest.approx(3.0)


def test_numero_br_e_erro_explicito():
    assert numero_localizado('1.234,56','m',True)==pytest.approx(1234.56)
    assert numero_localizado('1,25','m',True)==pytest.approx(1.25)
    with pytest.raises(ValueError,match='vírgula'):
        numero_localizado('1,25','m',False)


def test_carga_ficticia_so_para_validacao_do_importador():
    sample=('nome;massa [kg];X [m];Y [m];Z [m]\n'
            'caixa;100;1,2;0,5;0,8\n').encode()
    f=SimpleNamespace(name='cargas.csv',getvalue=lambda:sample)
    rows=ler(f,'cargas')
    assert identificar_tipo_tabela(rows[0])=='cargas'
    from utils.mapeamento import sugestao_coluna
    cols=['nome','massa_kg','x_m','y_m','z_m']
    map_={c:sugestao_coluna('cargas',c,rows[0]) for c in cols}
    rec=tabela_para_lista([{c:r[map_[c]] for c in cols} for r in rows],cols,decimal_virgula=True)
    assert rec[0]['x_m']==pytest.approx(1.2)


def test_ficha_grandeza_valor():
    f=SimpleNamespace(name='ficha.csv',getvalue=lambda:b'Grandeza;Valor\nnome;Navio X\nB;5.3\nD;2.7\nLPP;18\n')
    raw=ler(f,'barco')
    assert raw['B_m']=='5.3'
    assert 'L_m' not in raw


def test_unidade_literal_impede_erro_1000x():
    from utils.importacao import verificar_unidade_declarada
    assert verificar_unidade_declarada('Delta (deslocamento) [t]','t','deslocamento')
    assert verificar_unidade_declarada('km_m','m','km')
    with pytest.raises(ValueError,match='declara unidade'):
        verificar_unidade_declarada('Delta (deslocamento) [t]','kg','deslocamento')
    with pytest.raises(ValueError,match='declara unidade'):
        verificar_unidade_declarada('KM_t [m]','mm','KM transversal')

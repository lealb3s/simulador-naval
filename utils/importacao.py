"""Leitura defensiva de arquivos tabulares: arquivos e planilhas são dados, não fórmulas de engenharia.

Abas/cabeçalhos são identificados por esquema; cabeçalhos ambíguos não são
associados automaticamente. A unidade física exige confirmação no formulário.
"""
import csv
import io
from pathlib import Path
import pandas as pd
from .mapeamento import identificar_tipo_tabela, sugestao_coluna, simplificar


def _bytes(file):
    if isinstance(file, (bytes, bytearray)):
        return bytes(file)
    if hasattr(file, 'getvalue'):
        return file.getvalue()
    raise ValueError('Arquivo inválido: selecione um CSV, XLSX ou JSON.')


def _nome(file):
    return getattr(file, 'name', 'entrada.xlsx').lower()


def abas_excel(file):
    try:
        return pd.ExcelFile(io.BytesIO(_bytes(file))).sheet_names
    except Exception as exc:
        raise ValueError(f'Não foi possível abrir as abas do Excel: {exc}') from exc


def _ler_csv_bruto(file):
    data = _bytes(file)
    texto = None
    for enc in ('utf-8-sig', 'cp1252'):
        try:
            texto = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        raise ValueError('Não foi possível interpretar o texto CSV (UTF-8 ou Windows-1252).')
    amostra='\n'.join(l for l in texto.splitlines()[:15] if l.strip())
    try:
        delimiter=csv.Sniffer().sniff(amostra, delimiters=',;\t|').delimiter
    except csv.Error:
        delimiter=';' if ';' in amostra else '\t' if '\t' in amostra else ','
    try:
        rows=list(csv.reader(io.StringIO(texto),delimiter=delimiter))
    except csv.Error as exc:
        raise ValueError(f'CSV malformado: {exc}') from exc
    largura=max((len(r) for r in rows), default=0)
    if largura==0:
        raise ValueError('Arquivo CSV vazio.')
    return pd.DataFrame([r+['']*(largura-len(r)) for r in rows])


def ler_bruto(file, aba=None, nrows=None):
    nome=_nome(file)
    if nome.endswith('.csv'):
        df=_ler_csv_bruto(file)
        return df if nrows is None else df.head(nrows)
    if nome.endswith('.xlsx'):
        try:
            df=pd.read_excel(io.BytesIO(_bytes(file)),sheet_name=aba if aba is not None else 0,
                             header=None, nrows=nrows, dtype=object)
            return df
        except Exception as exc:
            raise ValueError(f'Não foi possível ler a aba "{aba or "primeira"}": {exc}') from exc
    raise ValueError('O leitor tabular aceita CSV e XLSX. Para JSON use a importação JSON.')


def _linhas_validas(bruto):
    for idx,row in bruto.iterrows():
        labels=[]
        for v in row.tolist():
            labels.append('' if pd.isna(v) else str(v).strip())
        if any(labels):
            yield idx, labels


def escolher_cabecalho(bruto, *, limite=35):
    """Localiza a linha de cabeçalho, sem adivinhar que uma grade de cotas é hidrostatica."""
    melhor=None
    for idx,labels in _linhas_validas(bruto.head(limite)):
        if len([x for x in labels if x])<2:
            continue
        tipo=identificar_tipo_tabela(labels)
        score={'global':10,'hidro':11,'gz':10,'cargas':9,'leituras':8,'casco':6,'barco':5}.get(tipo,0)
        if score==0:
            # Ainda permitir a escolha manual de cabeçalho em tabelas desconhecidas.
            score=0.01
        candidato=(score,-int(idx),int(idx),tipo)
        if melhor is None or candidato>melhor:
            melhor=candidato
    return (melhor[2],melhor[3]) if melhor else (0,None)


def montar_tabela(bruto, cabecalho_linha):
    if bruto.empty:
        return []
    if cabecalho_linha<0 or cabecalho_linha>=len(bruto):
        raise ValueError(f'Linha de cabeçalho {cabecalho_linha+1} fora da planilha.')
    cabecalhos=[]
    vistos={}
    for i,v in enumerate(bruto.iloc[cabecalho_linha].tolist(),1):
        titulo='' if pd.isna(v) else str(v).strip()
        if not titulo:
            titulo=f'Coluna sem título {i}'
        if titulo in vistos:
            raise ValueError(f'Cabeçalhos repetidos "{titulo}" nas colunas {vistos[titulo]} e {i}. '
                             'Corrija a origem ou selecione outra linha de cabeçalho.')
        vistos[titulo]=i
        cabecalhos.append(titulo)
    registros=[]
    for idx in range(cabecalho_linha+1,len(bruto)):
        vals=bruto.iloc[idx].tolist()
        if all(pd.isna(v) or str(v).strip()=='' for v in vals):
            continue
        r={'__linha_origem__':idx+1}
        for nome,v in zip(cabecalhos,vals):
            r[nome]=None if pd.isna(v) or str(v).strip()=='' else v
        registros.append(r)
    return registros


def ler_tabela(file, *, aba=None, cabecalho_linha=None):
    raw=ler_bruto(file,aba=aba)
    if cabecalho_linha is None:
        cabecalho_linha,_=escolher_cabecalho(raw)
    return montar_tabela(raw,int(cabecalho_linha))


def inspecionar_abas(file):
    """Retorna todos os diagnósticos; desconhecido significa não importar como outra tabela."""
    saida=[]
    for nome in abas_excel(file):
        try:
            raw=ler_bruto(file,aba=nome,nrows=38)
            cab,tipo=escolher_cabecalho(raw)
            nlinhas=sum(1 for i,_ in _linhas_validas(raw) if i>cab)
            msg='Compatível; confirme colunas, unidades e referencial.' if tipo else (
                'Estrutura não reconhecida: examine antes de importar; pode ser tabela auxiliar ou histórico.')
            saida.append({'aba':nome,'tipo':tipo,'linha_cabecalho':cab,
                          'linhas_amostra':nlinhas,'observacao':msg})
        except Exception as exc:
            saida.append({'aba':nome,'tipo':None,'linha_cabecalho':0,'linhas_amostra':0,
                          'observacao':f'Falha de leitura: {exc}'})
    return saida


def aliases_barco(registros):
    """Transforma cadastro campo/valor com somente equivalências físicas explícitas.
    LPP NÃO é sinônimo garantido de comprimento total da embarcação.
    """
    if not registros:
        raise ValueError('Ficha da embarcação vazia.')
    fields=list(registros[0].keys())
    k=next((x for x in fields if simplificar(x) in ('campo','grandeza','parametro','parâmetro')),None)
    v=next((x for x in fields if simplificar(x) in ('valor','value')),None)
    if k is not None and v is not None:
        raw={str(r.get(k) or '').strip():r.get(v) for r in registros if r.get(k) is not None}
    elif len(registros)==1:
        raw={k:v for k,v in registros[0].items() if k!='__linha_origem__'}
    else:
        raise ValueError('Ficha da embarcação: use duas colunas Grandeza/Valor (Campo/Valor) ou uma única linha.')
    equivalencias={'nome':'nome', 'b':'B_m','b [m]':'B_m','boca [m]':'B_m',
                   'd':'D_m','d [m]':'D_m','pontal [m]':'D_m',
                   'td':'calado_m', 't moldado [m]':'calado_m','calado [m]':'calado_m',
                   'l_m':'L_m','l [m]':'L_m', 'comprimento [m]':'L_m'}
    from .dados import BARCO_CAMPOS
    saida={};ignorados=[]
    for key,value in raw.items():
        normalized=simplificar(key)
        mapped=key if key in BARCO_CAMPOS else equivalencias.get(normalized)
        if mapped:
            if mapped in saida:
                raise ValueError(f'Ficha contém dois campos para {mapped}: confirme qual é correto.')
            saida[mapped]=value
        else:
            ignorados.append(key)
    return saida,ignorados


def unidade_declarada(nome_coluna):
    import re
    nome=simplificar(nome_coluna)
    # Campo canônico SI também declara a unidade.
    alias={'deslocamento_kg':'kg','massa_kg':'kg','calado_m':'m',
           'km_m':'m','kb_m':'m','lcb_m':'m','lcf_m':'m',
           'x_m':'m','y_m':'m','z_m':'m','comp_m':'m','larg_m':'m','alt_m':'m',
           'gz_m':'m','angulo_graus':'graus'}
    esperado=alias.get(nome)
    if nome.endswith("_kg"):
        esperado="kg"
    elif nome.endswith("_m") and not nome.endswith("por_m"):
        esperado="m"
    for tag in re.findall(r'\[([^]]+)\]|\(([^)]+)\)',nome):
        unit=(tag[0] or tag[1]).strip()
        if unit in ('t','kg','m','cm','mm','graus','°','deg','rad','radianos','n','kn','m3','m³','ft','lb','t.m/cm','t·m/cm','n·m','kn·m','kg·m','kg.m','kgm','kg·m/m','t·m','t.m'):
            esperado={'°':'graus','deg':'graus','rad':'radianos'}.get(unit,unit)
            break
    return esperado


def verificar_unidade_declarada(nome_coluna, unidade_escolhida, grandeza):
    nome = simplificar(nome_coluna)
    if grandeza=="km_m" and any(t in nome for t in ("km_l","kml","longitudinal","gm_t","kb [","kg [")):
        raise ValueError("KM transversal e a coluna escolhida representam grandezas diferentes.")
    esperado = unidade_declarada(nome_coluna)
    if esperado is not None and unidade_escolhida != esperado:
        raise ValueError(f"A coluna '{nome_coluna}' declara unidade '{esperado}', "
                         f"mas foi selecionado '{unidade_escolhida}' para {grandeza}. "
                         'Corrija a unidade ou confirme o cabeçalho na planilha original.')
    return True

"""I/O dos formatos CSV, XLSX e JSON. Importação validada; sem valores inventados."""
import io
import json
import pandas as pd
import numpy as np

BARCO_CAMPOS={"nome", "massa_base_kg","base_x_m","base_y_m","base_z_m",
              "L_m","B_m","D_m","deslocamento_referencia_kg","calado_m","km_m",
              "kb_m","lcb_m","lcf_m","mtc_kgm_por_m","fsm_kgm", "gz_deslocamento_kg", "gz_kg_referencia_m", "z_min_m", "z_max_m"}
COLUNAS_CARGAS=["id","nome","categoria","massa_kg","x_m","y_m","z_m","comp_m","larg_m","alt_m"]
COLUNAS_HIDRO=["deslocamento_kg","calado_m","km_m","kb_m","lcb_m","lcf_m","mtc_kgm_por_m"]
COLUNAS_GZ=["angulo_graus","gz_m"]
COLUNAS_CASCO=["x_m","y_m"]


def registro_vazio():
    b={k:None for k in BARCO_CAMPOS}
    b["nome"]="Embarcação sem identificação"
    b["hidro_tabela"]=[]
    b["gz_curva"]=[]
    b["casco_contorno"]=[]
    return b


def normalizar(obj):
    if isinstance(obj, dict): return {str(k):normalizar(v) for k,v in obj.items()}
    if isinstance(obj, (list,tuple)):return [normalizar(v) for v in obj]
    if isinstance(obj,np.generic):return normalizar(obj.item())
    if isinstance(obj,float) and not np.isfinite(obj):return None
    return obj


def ler(arquivo, tipo, *, aba=None, decimal_virgula=False, cabecalho_linha=None):
    """Importa qualquer aba selecionada sem converter uma tabela auxiliar em dados físicos."""
    from .importacao import ler_tabela, aliases_barco
    nome=arquivo.name.lower()
    dados=arquivo.getvalue()
    if nome.endswith(".json"):
        parsed=json.loads(dados.decode("utf-8-sig"))
        if tipo=="barco" and isinstance(parsed,dict):
            raw=parsed.get("barco",parsed)
            if not isinstance(raw,dict):raise ValueError("JSON de barco exige objeto")
            return raw
        if isinstance(parsed,dict):
            chave={"cargas":"cargas", "hidro":"hidro_tabela", "gz":"gz_curva", "casco":"casco_contorno", "leituras":"leituras"}.get(tipo)
            if tipo in ("hidro","gz","casco") and isinstance(parsed.get("barco"),dict):
                parsed=parsed["barco"].get(chave,[])
            else: parsed=parsed.get(chave,parsed)
        if not isinstance(parsed,list):raise ValueError("JSON: esperada uma lista de registros neste tipo")
        return normalizar(parsed)
    registros=ler_tabela(arquivo,aba=aba,cabecalho_linha=cabecalho_linha)
    if tipo=="barco":
        raw,_=aliases_barco(registros)
        return raw
    return normalizar(registros)


def numero_localizado(valor, campo, decimal_virgula=False, linha=None):
    """Conversão localizada explícita, sem substituir silenciosamente dados faltantes."""
    if isinstance(valor,bool):raise ValueError(f"{campo}: valor booleano não é número")
    if isinstance(valor,(int,float,np.integer,np.floating)):
        v=float(valor)
        if not np.isfinite(v):raise ValueError(f"{campo}: valor não finito")
        return v
    s=str(valor).strip().replace("\u00a0", "").replace(" ", "")
    if not s:raise ValueError(f"{campo}: número ausente")
    if decimal_virgula:
        if "." in s and "," in s:
            if s.rfind(",")<s.rfind("."):
                raise ValueError(f"{campo}: separadores incompatíveis com vírgula decimal: {valor}")
            s=s.replace(".", "")
        s=s.replace(",", ".")
    elif "," in s:
        if "." in s:
            raise ValueError(f"{campo}: número com vírgula decimal: ative a opção 'Vírgula decimal'")
        raise ValueError(f"{campo}: '{valor}' usa vírgula; confirme a convenção decimal no importador")
    try:v=float(s)
    except (TypeError,ValueError) as exc:raise ValueError(f"{campo}: número inválido '{valor}'") from exc
    if not np.isfinite(v):raise ValueError(f"{campo}: valor não finito")
    return v

def numero_digitado(valor):
    """Aceita ponto ou vírgula decimal nos campos de entrada manual."""
    return numero_localizado(valor, "Valor", decimal_virgula="," in str(valor))


def preparar_barco(obj, atual=None):
    base=registro_vazio() if atual is None else {**atual}
    for k,v in obj.items():
        if k in BARCO_CAMPOS:
            if k=="nome": base[k]=str(v)
            else:
                try:base[k]=None if v is None or str(v).strip()=="" else numero_digitado(v)
                except (ValueError, TypeError) as e:raise ValueError(f"Parâmetro '{k}' inválido") from e
        elif k in ("hidro_tabela","gz_curva","casco_contorno"):
            if not isinstance(v,list):raise ValueError(f"{k} precisa ser uma lista")
            base[k]=v
    from modules.validacao import numero, ordenar_hidro_tabela
    for campo in ("L_m","B_m","D_m","deslocamento_referencia_kg","gz_deslocamento_kg"):
        if base.get(campo) is not None:
            numero(base[campo], campo, positivo=True)
    if base.get("z_min_m") is not None and base.get("z_max_m") is not None and base["z_min_m"]>base["z_max_m"]:
        raise ValueError("Z mínimo deve ser menor ou igual ao máximo.")
    for campo in ("mtc_kgm_por_m","calado_m"):
        if base.get(campo) is not None:
            numero(base[campo],campo,positivo=True)
    for campo in ("massa_base_kg", "fsm_kgm"):
        if base.get(campo) is not None:
            numero(base[campo], campo, nao_negativo=True)
    for campo, colunas in (("gz_curva", COLUNAS_GZ), ("casco_contorno", COLUNAS_CASCO)):
        if campo in obj:
            linhas = tabela_para_lista(base[campo], colunas)
            if any(linha[c] is None for linha in linhas for c in colunas):
                raise ValueError(f"{campo}: preencha as duas coordenadas de cada linha")
            base[campo] = linhas
    if "hidro_tabela" in obj:
        base["hidro_tabela"] = ordenar_hidro_tabela(base["hidro_tabela"])
    return base


def tabela_para_lista(linhas, colunas, *, decimal_virgula=False):
    """Converte linhas mapeadas; ignorando somente linhas TOTALMENTE vazias."""
    if linhas:
        cabecalhos=set().union(*(set(linha) for linha in linhas if isinstance(linha,dict)))
        if not (cabecalhos & set(colunas)):
            raise ValueError("Colunas não reconhecidas. Esperadas: "+", ".join(colunas)+
                             ". Encontradas: "+", ".join(map(str, sorted(cabecalhos, key=str))))
    out=[]
    for n,row in enumerate(linhas):
        if not isinstance(row,dict):raise ValueError(f"Registro {n+1} não é objeto")
        numero_linha=row.get('__linha_origem__',n+1)
        linha={}
        for c in colunas:
            v=row.get(c)
            if v is None or str(v).strip()=="" or (isinstance(v,(float,np.floating)) and np.isnan(v)):
                linha[c]=None
            elif c in ("nome","categoria","id"):
                linha[c]=str(v).strip()
            else:
                linha[c]=numero_localizado(v,f"linha {numero_linha} / {c}",decimal_virgula)
        if any(v is not None for v in linha.values()):
            if '__linha_origem__' in row and row['__linha_origem__'] is not None:
                linha['__linha_origem__']=row['__linha_origem__']
            out.append(linha)
    return out

def csv_bytes(rows, colunas=None):
    return pd.DataFrame(rows, columns=colunas).to_csv(index=False).encode("utf-8-sig")


def json_bytes(data):
    return json.dumps(normalizar(data),indent=2,ensure_ascii=False).encode("utf-8")

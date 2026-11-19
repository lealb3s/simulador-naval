from utils.navegacao import atalho
from utils.dados import numero_digitado
import copy
import pandas as pd
import streamlit as st
from modules.validacao import ordenar_hidro_tabela
from utils.estado import inicializar, aplicar, alternar_projeto
from utils.mapeamento import identificar_tipo_tabela
from utils.dados import ler, preparar_barco, registro_vazio, tabela_para_lista, COLUNAS_HIDRO, COLUNAS_GZ, COLUNAS_CASCO, json_bytes, csv_bytes
from utils.ui_importacao import fonte_tabela, selecionar_unidade, transferir_aba, controles_tabela, mapear_campos, aplicar_mapeamento
from utils.importacao import verificar_unidade_declarada,aliases_barco

def render():
    inicializar()
    st.title("Embarcação")
    if st.session_state.get("exemplo_ativo"):
        if st.button("Abrir entrada manual",type="primary"):
            alternar_projeto(False)
            st.rerun()
        if not st.checkbox("Consultar ou editar a ficha do pontão fictício"):
            return
    if st.session_state.prova_em_andamento:
        st.info("A condição está congelada durante a prova. Encerre o ensaio para voltar a editar.")
        atalho("ensaio", "Retomar o ensaio ativo")
        return
    st.write("Importe a ficha da embarcação ou preencha os parâmetros manuais. Se tiver uma tabela hidrostática, confira a aba, as colunas e as unidades antes de salvá-la.")
    from utils.condicao_global import painel
    def painel_importacao():
        with st.expander("Importar dados — barco, hidrostática, GZ ou contorno", expanded=True):
            st.caption("Envie primeiro o arquivo. Para CSV/XLSX, a categoria é sugerida pelos cabeçalhos; confira antes de importar.")
            uploaded=fonte_tabela("Selecione CSV, XLSX ou JSON","embarcacao","upload_embarcacao")
            if uploaded:
                try:
                    aba,linha_cabecalho,decimal_virgula,sugerido=controles_tabela(uploaded,'embarcacao', ('barco','hidro','gz','casco'))
                    eh_json=uploaded.name.lower().endswith('.json')
                    preliminares=(ler(uploaded,'hidro',aba=aba,decimal_virgula=decimal_virgula,
                                     cabecalho_linha=linha_cabecalho) if not eh_json else None)
                    cabecalhos=list(dict.fromkeys(k for r in (preliminares or []) if isinstance(r,dict)
                                                for k in r if k!='__linha_origem__'))
                    # Reclassifica se a linha de cabeçalho foi alterada manualmente.
                    if preliminares is not None:sugerido=identificar_tipo_tabela(cabecalhos)
                    if eh_json:
                        import json
                        estrutura = json.loads(uploaded.getvalue().decode('utf-8-sig'))
                        if isinstance(estrutura,dict) and ("condicoes" in estrutura or identificar_tipo_tabela(estrutura)=="global"):
                            sugerido="global"
                        elif isinstance(estrutura, dict) and ('barco' in estrutura or set(estrutura) & set(registro_vazio()) - {'hidro_tabela','gz_curva','casco_contorno'}):
                            sugerido = 'barco'
                        elif isinstance(estrutura, list) and estrutura and isinstance(estrutura[0], dict):
                            sugerido = identificar_tipo_tabela(estrutura[0])
                    tipos=['— Escolha o tipo de dado —','barco','hidro','gz','casco','global','cargas','leituras','livre']
                    nomes={'cargas':'Cargas','leituras':'Medições experimentais','livre':'Tabela livre (consulta)','global':'Condição global de carregamento','barco':'Parâmetros da embarcação','hidro':'Tabela hidrostática',
                           'gz':'Curva GZ','casco':'Contorno do casco em planta (X,Y)'}
                    import hashlib
                    uid=hashlib.sha1(uploaded.getvalue()).hexdigest()[:10]
                    opcoes_tipo = {nomes.get(t, t): t for t in tipos}
                    rotulo = st.selectbox('Tipo de dado', list(opcoes_tipo),
                                          index=tipos.index(sugerido) if sugerido in tipos else 0,
                                          key=f'tipo_embarcacao_{uid}_{aba}_{linha_cabecalho}')
                    tipo = opcoes_tipo[rotulo]
                    if tipo=="global":
                        painel(uploaded,(aba,linha_cabecalho,decimal_virgula,sugerido))
                        return
                    if tipo=="livre":
                        registros=preliminares
                        if eh_json:
                            registros=estrutura if isinstance(estrutura,list) else [estrutura]
                        tabela=pd.DataFrame(registros).drop(columns=["__linha_origem__"],errors="ignore")
                        st.dataframe(tabela,width="stretch",hide_index=True)
                        titulo=st.text_input("Nome da tabela",value=aba or uploaded.name,key="titulo_livre_"+uid)
                        if tabela.empty:
                            st.info("Ajuste o intervalo ou marque Tabela sem cabeçalho para incluir a primeira linha.")
                            return
                        if st.button("Guardar tabela para consulta"):
                            if not titulo.strip():
                                raise ValueError("Informe um nome para a tabela.")
                            st.session_state.setdefault("tabelas_livres",{})[titulo.strip()]=tabela.to_csv(index=False)
                            st.success("Tabela disponível para consulta e no JSON de resultados.")
                        return
                    if tipo in ('cargas','leituras'):
                        pagina='Carregamento' if tipo=='cargas' else 'Processamento'
                        destino='cargas' if tipo=='cargas' else 'processamento'
                        if st.button(f'Abrir esta tabela em {pagina}'):
                            transferir_aba(uploaded,destino,aba,linha_cabecalho,decimal_virgula)
                        return
                    if sugerido in nomes:
                        st.info(f'A aba parece conter **{nomes.get(sugerido,sugerido)}**. '
                                'Confirme os campos e as unidades antes de importar.')
                    if tipo=='— Escolha o tipo de dado —':
                        if sugerido in ('cargas','leituras'):
                            return
                        st.info('Selecione o tipo de dado para associar as colunas, ou escolha Tabela livre para guardar e consultar o conteúdo.')
                        return
                    if tipo=="barco" and sugerido=="hidro":
                        raise ValueError("Esta planilha contém várias condições hidrostáticas, não uma ficha de parâmetros do barco. "
                                         "Escolha 'Tabela hidrostática' em 'Tipo de dado'.")
                    dados=(preliminares if tipo!="barco" and preliminares is not None
                           else ler(uploaded,tipo,aba=aba,decimal_virgula=decimal_virgula,cabecalho_linha=linha_cabecalho))
                    if tipo!="barco":
                        if not isinstance(dados,list) or not dados or not isinstance(dados[0],dict):
                            raise ValueError("A tabela selecionada está vazia ou não contém registros tabulares")
                        col={"hidro":COLUNAS_HIDRO,"gz":COLUNAS_GZ,"casco":COLUNAS_CASCO}[tipo]
                        obrig={"hidro":["deslocamento_kg","calado_m","km_m"],
                               "gz":COLUNAS_GZ,"casco":COLUNAS_CASCO}[tipo]
                        with st.container(border=True):
                            st.markdown('**Associe os campos originais aos campos do simulador.**')
                            mapeamento=mapear_campos(dados,tipo,col,obrig,
                                          f'embarcacao_{uid}_{aba}_{linha_cabecalho}')
                            if tipo=='hidro':
                                st.info('Importe somente deslocamento, calado, KM transversal e grandezas opcionais. '
                                        'Não use KM longitudinal como KM transversal; KG/GM vazios são aceitáveis.')
                            fator_m=1.0
                            fator_kg=1.0
                            fator_graus=1.0
                            if tipo=="hidro":
                                ua,ub=st.columns(2)
                                unidade_peso=selecionar_unidade(ua,"Unidade do deslocamento na tabela *",["Selecione","kg","t (tonelada métrica)"], mapeamento, ('deslocamento_kg',), f"unid_delta_hidro_{uid}_{aba}_{linha_cabecalho}")
                                unidade_comp=selecionar_unidade(ub,"Unidade de calado, KM, KB, LCB e LCF na tabela *",["Selecione","m","cm","mm"], mapeamento, ('calado_m', 'km_m', 'kb_m', 'lcb_m', 'lcf_m'), f"unid_comp_hidro_{uid}_{aba}_{linha_cabecalho}")
                                fator_kg={"kg":1.0,"t (tonelada métrica)":1000.0}.get(unidade_peso)
                                fator_m={"m":1.0,"cm":0.01,"mm":0.001}.get(unidade_comp)
                                st.caption("MCT é importado sem conversão: deve estar em kg·m por metro de trim. Se tiver outra unidade, converta-o antes de importar.")
                            elif tipo=="gz":
                                ua,ub=st.columns(2)
                                unidade_ang=selecionar_unidade(ua,"Unidade do ângulo na tabela *",["Selecione","graus","radianos"], mapeamento, ('angulo_graus',), f"unid_angulo_gz_{uid}_{aba}_{linha_cabecalho}")
                                unidade_comp=selecionar_unidade(ub,"Unidade do GZ na tabela *",["Selecione","m","cm","mm"], mapeamento, ('gz_m',), f"unid_comp_gz_{uid}_{aba}_{linha_cabecalho}")
                                from math import degrees
                                fator_graus={"graus":1.0,"radianos":degrees(1.0)}.get(unidade_ang)
                                fator_m={"m":1.0,"cm":0.01,"mm":0.001}.get(unidade_comp)
                            else:
                                unidade_comp=selecionar_unidade(st,"Unidade das coordenadas X e Y na tabela *",["Selecione","m","cm","mm"], mapeamento, ('x_m', 'y_m'), f"unid_comp_casco_{uid}_{aba}_{linha_cabecalho}")
                                fator_m={"m":1.0,"cm":0.01,"mm":0.001}.get(unidade_comp)
                        # Prévia dos dados de origem, sem modificar os números.
                        st.dataframe(pd.DataFrame(dados).head(8),width="stretch")
                    if tipo=='barco':
                        st.dataframe(pd.DataFrame([{'Parâmetro':k,'Valor recebido':str(v) if not isinstance(v,list) else f'{len(v)} registros'} for k,v in dados.items()]),
                                     width="stretch",hide_index=True)
                        st.caption('LPP não é convertido automaticamente em L_m. A identificação do referencial é necessária.')
                        if preliminares is not None:
                            _dados_barco,_ignorados=aliases_barco(preliminares)
                            if _ignorados:
                                st.warning('Grandezas não associadas automaticamente: '+', '.join(_ignorados)+
                                           '. Preencha manualmente os parâmetros não reconhecidos, quando aplicável.')
                        # Um Excel de dados principais pode omitir a unidade de B, D e Td.
                        # Exigir que o usuário a confirme impede assumir SI sem evidência.
                        _campos_metrico={'L_m','B_m','D_m','calado_m','km_m','kb_m','lcb_m','lcf_m',
                                         'base_x_m','base_y_m','base_z_m','gz_kg_referencia_m',
                                         'z_min_m','z_max_m'}
                        _campos_massa={'massa_base_kg','deslocamento_referencia_kg','gz_deslocamento_kg'}
                        _tem_comp=any(k in dados and dados[k] is not None and str(dados[k]).strip()
                                      for k in _campos_metrico)
                        _tem_massa=any(k in dados and dados[k] is not None and str(dados[k]).strip()
                                      for k in _campos_massa)
                        if eh_json:
                            st.info('JSON do simulador: pressupõe campos canônicos em SI, conforme documentação.')
                            unidade_barco_comp='m';unidade_barco_massa='kg'
                        else:
                            unidade_barco_comp=(st.selectbox('Unidade das dimensões da ficha *',
                                                  ['Selecione','m','cm','mm'],
                                                  key=f'unid_ficha_comp_{uid}_{aba}') if _tem_comp else 'm')
                            unidade_barco_massa=(st.selectbox('Unidade das massas da ficha *',
                                                  ['Selecione','kg','t (tonelada métrica)'],
                                                  key=f'unid_ficha_massa_{uid}_{aba}') if _tem_massa else 'kg')
                    if st.button("Validar e importar",type="primary",key=f"btn_import_{uid}_{aba}_{tipo}"):
                        if tipo=="barco":
                            if not dados or not set(dados).intersection(registro_vazio()):
                                raise ValueError('Não há parâmetros reconhecidos. Confira a aba e os nomes dos campos.')
                            from utils.dados import numero_localizado
                            if unidade_barco_comp=='Selecione' or unidade_barco_massa=='Selecione':
                                raise ValueError('Confirme a unidade das dimensões e massas desta ficha.')
                            for key, val in list(dados.items()):
                                if key=='nome' or isinstance(val,(list,dict)) or val is None or not str(val).strip():
                                    continue
                                numeric=numero_localizado(val,key,decimal_virgula)
                                if key in _campos_metrico:
                                    numeric *= {'m':1.0,'cm':0.01,'mm':0.001}[unidade_barco_comp]
                                elif key in _campos_massa:
                                    numeric *= {'kg':1.0,'t (tonelada métrica)':1000.0}[unidade_barco_massa]
                                dados[key]=numeric
                            novo=preparar_barco(dados,copy.deepcopy(st.session_state.barco))
                            # Uma tabela importada previamente permanece intacta, mas deve ser válida.
                            novo["hidro_tabela"]=ordenar_hidro_tabela(novo.get("hidro_tabela",[]))
                        else:
                            faltantes=[campo for campo in obrig if mapeamento[campo]=="— Não importar —"]
                            if faltantes:
                                raise ValueError("Associe as colunas obrigatórias: "+", ".join(faltantes)+". Se não existirem, importe uma tabela adequada.")
                            ativos=[c for c in mapeamento.values() if c!="— Não importar —"]
                            if len(ativos)!=len(set(ativos)):
                                raise ValueError("Uma coluna do arquivo foi associada a mais de um campo. Corrija o mapeamento.")
                            if fator_m is None or fator_kg is None or fator_graus is None:
                                raise ValueError("Confirme explicitamente as unidades dos valores no arquivo antes de importar.")
                            # Evita tratar tonelada como quilograma ou milímetro como metro
                            # quando a unidade está expressa literalmente no cabeçalho.
                            if tipo=='hidro':
                                mct_header = mapeamento.get("mtc_kgm_por_m")
                                if mct_header and mct_header != "— Não importar —":
                                    verificar_unidade_declarada(mct_header,"kg·m/m","mtc_kgm_por_m")
                                for field in ('deslocamento_kg',):
                                    header=mapeamento.get(field)
                                    if header!='— Não importar —':
                                        verificar_unidade_declarada(header,'t' if unidade_peso.startswith('t ') else unidade_peso,field)
                                for field in ('calado_m','km_m','kb_m','lcb_m','lcf_m'):
                                    header=mapeamento.get(field)
                                    if header!='— Não importar —':
                                        verificar_unidade_declarada(header,unidade_comp,field)
                            elif tipo=='gz':
                                for field,selected in (('angulo_graus',unidade_ang),('gz_m',unidade_comp)):
                                    header=mapeamento.get(field)
                                    if header!='— Não importar —':
                                        verificar_unidade_declarada(header,selected,field)
                            else:
                                for field in ('x_m','y_m'):
                                    header=mapeamento.get(field)
                                    if header!='— Não importar —':
                                        verificar_unidade_declarada(header,unidade_comp,field)
                            linhas=aplicar_mapeamento(dados,mapeamento,obrig)
                            registros=tabela_para_lista(linhas,col,decimal_virgula=decimal_virgula)
                            if not registros:
                                raise ValueError("A importação está vazia; confira a aba e as linhas da tabela.")
                            if tipo=="hidro":
                                for r in registros:
                                    if r["deslocamento_kg"] is not None: r["deslocamento_kg"]*=fator_kg
                                    for campo in ("calado_m","km_m","kb_m","lcb_m","lcf_m"):
                                        if r[campo] is not None: r[campo]*=fator_m
                                registros=ordenar_hidro_tabela(registros)
                                chave="hidro_tabela"
                            elif tipo=="gz":
                                for i,r in enumerate(registros,1):
                                    if r["angulo_graus"] is None or r["gz_m"] is None:
                                        raise ValueError(f"Curva GZ: linha {r.get('__linha_origem__',i)}, preencha ângulo e GZ")
                                    r["angulo_graus"]*=fator_graus
                                    r["gz_m"]*=fator_m
                                registros.sort(key=lambda r:r["angulo_graus"])
                                chave="gz_curva"
                            else:
                                for i,r in enumerate(registros,1):
                                    if r["x_m"] is None or r["y_m"] is None:
                                        raise ValueError(f"Contorno: linha {r.get('__linha_origem__',i)}, informe X e Y")
                                    r["x_m"]*=fator_m
                                    r["y_m"]*=fator_m
                                chave="casco_contorno"
                            # Preserva a origem da linha apenas para diagnóstico; não grava como grandeza física.
                            for r in registros:r.pop('__linha_origem__',None)
                            novo=copy.deepcopy(st.session_state.barco)
                            novo[chave]=registros
                        aplicar(novo_barco=novo,descricao="Importação "+tipo)
                        st.success(f"Importação concluída · {nomes[tipo]}.")
                except Exception as e:
                    st.error("Não foi possível importar: "+str(e))
                    st.info("Confira o tipo de tabela, a aba do Excel, os cabeçalhos e as unidades; se necessário, envie o arquivo para conferir o mapeamento.")


    if st.session_state.get("tabelas_livres"):
        with st.expander("Tabelas guardadas para consulta"):
            import io
            nome_livre=st.selectbox("Tabela",list(st.session_state.tabelas_livres))
            texto=st.session_state.tabelas_livres[nome_livre]
            st.dataframe(pd.read_csv(io.StringIO(texto),dtype=str,keep_default_na=False),hide_index=True)
            st.download_button("Baixar tabela em CSV",texto.encode("utf-8-sig"),file_name="tabela.csv",mime="text/csv")
    modo = "exemplo" if st.session_state.get("exemplo_ativo") else "manual"
    with st.expander("Ficha do pontão fictício" if modo=="exemplo" else "Ficha da embarcação · entrada manual", expanded=True), st.form("barco_"+modo):
        b=st.session_state.barco
        st.caption("Para o ensaio virtual, informe a massa base, seus centros e o momento de superfície livre. A referência hidrostática pode vir da tabela importada.")
        nome=st.text_input("Identificação",value=b.get("nome") or "")
        desc={"massa_base_kg":"Massa base — exclui cargas cadastradas (kg)","base_x_m":"LCG da massa base (m)","base_y_m":"TCG da massa base (m)","base_z_m":"KG da massa base (m)",
              "L_m":"Comprimento (m)","B_m":"Boca (m)","D_m":"Pontal (m)","z_min_m":"Limite mínimo físico de Z (m; opcional)","z_max_m":"Limite máximo físico de Z (m; opcional)","deslocamento_referencia_kg":"Deslocamento de referência (kg)",
              "calado_m":"Calado de referência (m)","km_m":"KM transversal de referência (m)","kb_m":"KB de referência (m)",
              "lcb_m":"LCB de referência (m)","lcf_m":"LCF de referência (m)","mtc_kgm_por_m":"MCT — momento por 1 m de trim (kg·m/m)",
              "fsm_kgm":"Momento de superfície livre efetivo (kg·m; 0 se comprovadamente ausente)",
              "gz_deslocamento_kg":"Deslocamento correspondente à curva GZ (kg)","gz_kg_referencia_m":"KG da curva GZ importada (m)"}
        inputs={}
        grupos = {
            "Massa e centros": ("massa_base_kg", "base_x_m", "base_y_m", "base_z_m", "fsm_kgm"),
            "Dimensões e limites": ("L_m", "B_m", "D_m", "z_min_m", "z_max_m"),
            "Referência hidrostática": ("deslocamento_referencia_kg", "km_m", "calado_m", "kb_m", "lcb_m", "lcf_m", "mtc_kgm_por_m"),
            "Referência da curva GZ": ("gz_deslocamento_kg", "gz_kg_referencia_m"),
        }
        for titulo, campos in grupos.items():
            st.markdown(f"**{titulo}**")
            cols = st.columns(2)
            for i, key in enumerate(campos):
                inputs[key] = cols[i % 2].text_input(desc[key], value="" if b.get(key) is None else str(b[key]),
                    key=f"{'pontao' if modo=='exemplo' else 'barco'}_{st.session_state.revisao_barco}_{key}")
        if st.form_submit_button("Salvar dados manuais"):
            try:
                novo=preparar_barco({"nome":nome,**inputs},b)
                for k in ("massa_base_kg","L_m","B_m","D_m","deslocamento_referencia_kg"):
                    if novo.get(k) is not None and novo[k]<(0 if k=="massa_base_kg" else 1e-300):raise ValueError(f"{k} deve ser não negativo para massa base, positivo nos demais")
                if novo.get("fsm_kgm") is not None and novo["fsm_kgm"]<0:raise ValueError("FSM não pode ser negativo")
                aplicar(novo_barco=novo,descricao="Atualização manual dos dados")
                st.success("Parâmetros salvos")
            except ValueError as e:st.error(str(e))

    painel_importacao()
    st.divider()
    st.subheader("Tabelas e entrada manual")
    for tipo,col,chave in [("Hidrostática",COLUNAS_HIDRO,"hidro_tabela"),("Curva GZ",COLUNAS_GZ,"gz_curva"),("Casco planta",COLUNAS_CASCO,"casco_contorno")]:
        with st.expander(tipo):
            linhas=st.session_state.barco[chave]
            df=pd.DataFrame(linhas,columns=col,dtype=float)
            editado=st.data_editor(df,num_rows="dynamic",key=f"edit_{chave}_{st.session_state.revisao_barco}",width="stretch")
            if st.button("Salvar tabela "+tipo,key="btn_"+chave):
                try:
                    novo=copy.deepcopy(st.session_state.barco)
                    novo[chave]=tabela_para_lista(editado.to_dict("records"),col)
                    if chave=="hidro_tabela":
                        novo[chave] = ordenar_hidro_tabela(novo[chave])
                    elif chave=="gz_curva":
                        if any(r["angulo_graus"] is None or r["gz_m"] is None for r in novo[chave]):raise ValueError("Preencha ângulo e GZ")
                        novo[chave]=sorted(novo[chave],key=lambda r:r["angulo_graus"])
                    elif chave=="casco_contorno":
                        if any(r["x_m"] is None or r["y_m"] is None for r in novo[chave]):raise ValueError("Contorno exige X e Y")
                    aplicar(novo_barco=novo,descricao="Salvar "+tipo)
                    st.success("Tabela salva")
                except Exception as e:st.error(str(e))
            st.download_button("Exportar CSV "+tipo,csv_bytes(st.session_state.barco[chave],col),file_name=chave+".csv",key="download_"+chave)
    if st.session_state.barco.get("gz_curva"):
        import plotly.express as px
        curva = sorted(st.session_state.barco["gz_curva"],key=lambda r:r["angulo_graus"])
        st.plotly_chart(px.line(curva,x="angulo_graus",y="gz_m",labels={"angulo_graus":"Banda (°)","gz_m":"GZ (m)"},title="Curva GZ fornecida · condição de origem"),width="stretch")
    st.download_button("Exportar dados do barco (JSON)",json_bytes(st.session_state.barco),file_name="embarcacao.json")
    st.caption("Tabela hidrostática: deslocamento kg e calado/KM m, ordenados. Interpolação apenas dentro da faixa. A curva GZ só será adaptada para outro KG se deslocamento e superfície livre permitirem.")

    st.divider()
    with st.expander("Calcular a massa base a partir de uma condição global"):
        st.write("Se você conhece o **deslocamento total** e CG global, e você já cadastrou as cargas individuais dessa condição, é possível recuperar a massa/CG remanescente (base) por balanço de momentos. A operação não altera o cadastro até sua confirmação.")
        with st.form("recuperar_base_global"):
            a,b,c,d=st.columns(4)
            deslocamento_total=a.text_input("Δ total (kg)",key="global_delta")
            lcg_total=b.text_input("LCG total (m)",key="global_lcg")
            tcg_total=c.text_input("TCG total (m)",key="global_tcg")
            kg_total=d.text_input("KG total (m)",key="global_kg")
            if st.form_submit_button("Derivar massa base por balanço de momentos"):
                try:
                    if not all([deslocamento_total,lcg_total,tcg_total,kg_total]):raise ValueError("Para a massa e todos os centros, informe Δ, LCG, TCG e KG totais")
                    total=numero_digitado(deslocamento_total)
                    cargas=st.session_state.cargas
                    from modules.carregamento import base_da_condicao
                    centros = dict(lcg_m=numero_digitado(lcg_total),tcg_m=numero_digitado(tcg_total),kg_m=numero_digitado(kg_total))
                    base = base_da_condicao(total,centros,cargas)
                    mb=base["massa_base_kg"]
                    novo={**st.session_state.barco, **base}
                    aplicar(novo_barco=novo,descricao="Derivar base da condição global")
                    st.success(f"Massa base derivada: {mb:.6g} kg; centros recuperados por Σm·r/Δ. Confirme o referencial de coordenadas.")
                except Exception as ex:st.error(str(ex))


render()

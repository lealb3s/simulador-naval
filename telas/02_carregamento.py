from utils.navegacao import selecionar_carga
from utils.navegacao import atalho
from utils.dados import numero_digitado
import copy
import pandas as pd
import streamlit as st
from modules.carregamento import calcular, propor_posicoes
from modules.validacao import verificar_carga
from modules.hidrostatica import consultar, trim_estatico
from modules.estabilidade import avaliar, gz_adaptada
from utils.estado import inicializar, aplicar, historico, restaurar_cargas, nova_id
from utils.dados import ler, tabela_para_lista, COLUNAS_CARGAS, csv_bytes
from utils.ui_importacao import fonte_tabela, selecionar_unidade, arquivo_recebido,controles_tabela,mapear_campos,aplicar_mapeamento
from utils.importacao import verificar_unidade_declarada
from visualization.casco import planta
from visualization.cargas import perfil
from utils.planta_interativa import planta_editavel

def render():
    inicializar(); st.title("Carregamento")
    if st.session_state.prova_em_andamento:
        st.info("A condição está congelada durante a prova. Encerre o ensaio para voltar a editar.")
        atalho("ensaio", "Retomar o ensaio ativo")
        return
    st.caption("Modo carregamento: adicionar/remover altera Δ; reposicionar mantém Δ. As coordenadas são do CG individual, não de um vértice do objeto.")
    barco=st.session_state.barco
    painel_planta=st.empty()
    faltantes=[(k,r) for k,r in (("L_m","Comprimento"),("B_m","Boca"),("D_m","Pontal")) if not barco.get(k)]
    if faltantes:
        with st.expander("Dimensões para posicionar as cargas",expanded=not barco.get("L_m") or not barco.get("B_m")):
            st.caption("Informe comprimento e boca para abrir a planta. O pontal permite sugerir a altura das cargas quando Z estiver vazio.")
            with st.form("dimensoes_planta"):
                cols=st.columns(len(faltantes))
                dim={k:col.number_input(rotulo+" da embarcação (m)",min_value=0.000001,value=None,format="%.5f")
                     for col,(k,rotulo) in zip(cols,faltantes)}
                if st.form_submit_button("Salvar dimensões da embarcação"):
                    aplicar(novo_barco={**barco,**{k:v for k,v in dim.items() if v is not None}},descricao="Dimensões para a planta")
                    st.rerun()
    with st.expander("Importar tabela de cargas", expanded=bool(st.session_state.get("tabela_para_cargas")) or not st.session_state.cargas):
        f=fonte_tabela("Importar cargas (CSV/XLSX/JSON)","cargas")
        f = arquivo_recebido(f, "cargas")
        if f:
            try:
                import hashlib
                uid=hashlib.sha1(f.getvalue()).hexdigest()[:10]
                aba,head,decimal_virgula,sugerido=controles_tabela(f,'cargas', ('cargas',))
                rows=ler(f,'cargas',aba=aba,cabecalho_linha=head,decimal_virgula=decimal_virgula)
                if not rows:raise ValueError('A aba de cargas não contém dados.')
                st.dataframe(pd.DataFrame(rows).drop(columns=['__linha_origem__'],errors='ignore').head(8),
                             width="stretch",hide_index=True)
                if f.name.lower().endswith('.json'):
                    st.info('JSON no esquema do simulador: massa em kg e coordenadas em m.')
                    mapped=rows;factor_mass=1.0;factor_coord=1.0
                else:
                    if sugerido not in (None,'cargas'):
                        st.warning('A aba parece conter outra categoria de dados. Confira antes de importar.')
                    colmap=mapear_campos(rows,'cargas',COLUNAS_CARGAS,
                                         ['massa_kg'],f'cargas_map_{uid}_{aba}_{head}')
                    c1,c2=st.columns(2)
                    mass_unit=selecionar_unidade(c1,'Massa na planilha *',['Selecione','kg','t (tonelada métrica)'], colmap, ('massa_kg',), f'cargas_unidade_massa_{uid}_{aba}')
                    medidas=('x_m','y_m','z_m','comp_m','larg_m','alt_m')
                    tem_medidas=any(colmap[k]!='— Não importar —' for k in medidas)
                    length_unit=selecionar_unidade(c2,'Posições e dimensões na planilha *',['Selecione','m','cm','mm'],colmap,medidas,f'cargas_unidade_comp_{uid}_{aba}') if tem_medidas else 'm'
                    factor_mass={'kg':1.0,'t (tonelada métrica)':1000.0}.get(mass_unit)
                    factor_coord={'m':1.0,'cm':0.01,'mm':0.001}.get(length_unit)
                    mapped=None
                campo_nome="nome" if mapped is not None else colmap.get("nome")
                nomes_de_resumo={"total","total geral","subtotal","sub-total"}
                linhas_resumo={i for i,r in enumerate(rows)
                              if str(r.get(campo_nome,"")).strip().casefold() in nomes_de_resumo}
                ignorar_resumo=False
                if linhas_resumo:
                    ignorar_resumo=st.checkbox(f"Excluir linhas de total ou subtotal ({len(linhas_resumo)})",
                                               value=True,key="resumo_"+uid)
                sugerir_import=st.checkbox("Sugerir posições para as coordenadas vazias",value=True,key="propor_"+uid)
                st.caption("As coordenadas existentes têm prioridade. Para campos vazios, o app pode distribuir X pelo comprimento, usar a linha de centro em Y e metade do pontal em Z. Confira as posições sugeridas na planta.")
                if st.button('Validar e substituir cargas importadas',type='primary',key=f'btn_importar_cargas_{uid}_{aba}'):
                    if factor_mass is None or factor_coord is None:
                        raise ValueError('Confirme as unidades de massa e distância antes da importação.')
                    if mapped is None:
                        for field in ('massa_kg',):
                            header=colmap.get(field)
                            if header!='— Não importar —':
                                verificar_unidade_declarada(header,'t' if mass_unit.startswith('t ') else mass_unit,field)
                        for field in ('x_m','y_m','z_m','comp_m','larg_m','alt_m'):
                            header=colmap.get(field)
                            if header!='— Não importar —':
                                verificar_unidade_declarada(header,length_unit,field)
                        mapped=aplicar_mapeamento(rows,colmap,['massa_kg'])
                    if ignorar_resumo:
                        mapped=[r for i,r in enumerate(mapped) if i not in linhas_resumo]
                    cargas=tabela_para_lista(mapped,COLUNAS_CARGAS,decimal_virgula=decimal_virgula)
                    if not cargas:raise ValueError('Não há cargas para importar.')
                    for i,c in enumerate(cargas,1):
                        if not c.get('nome'):c['nome']=c.get('id') or f'Carga {i}'
                        if not c.get('id'):c['id']=nova_id()
                        if not c.get('categoria'):c['categoria']='Sem categoria'
                        if c['massa_kg'] is not None:c['massa_kg']*=factor_mass
                        for key in ('x_m','y_m','z_m','comp_m','larg_m','alt_m'):
                            if c[key] is not None:c[key]*=factor_coord
                    if sugerir_import:
                        propor_posicoes(cargas,barco)
                    for i,c in enumerate(cargas,1):
                        try:verificar_carga(c,st.session_state.barco)
                        except ValueError as exc:
                            raise ValueError(f'Linha {c.get("__linha_origem__",i)} / carga {c.get("nome")}: {exc}') from exc
                    if len({c['id'] for c in cargas})!=len(cargas):
                        raise ValueError('IDs duplicados: revise os identificadores na planilha.')
                    for c in cargas:c.pop('__linha_origem__',None)
                    aplicar(novas_cargas=cargas,descricao='Importar cargas')
                    st.session_state.cargas_inicio=copy.deepcopy(cargas)
                    st.success(f'{len(cargas)} cargas importadas após validação de dados e unidades.')
            except Exception as e:st.error('Falha de importação de cargas: '+str(e))
    with st.expander("Adicionar nova carga",expanded=not st.session_state.cargas):
        with st.form("add_carga"):
            nome=st.text_input("Nome");categoria=st.text_input("Categoria",value="Carga")
            massastr=st.text_input("Massa (kg)")
            a,b,c=st.columns(3)
            xstr=a.text_input("X (m)");ystr=b.text_input("Y (m)");zstr=c.text_input("Z (m)")
            sugerir=st.checkbox("Sugerir as coordenadas deixadas em branco",value=True)
            d1,d2,d3=st.columns(3)
            comp=d1.text_input("Comprimento da carga (m; opcional)");larg=d2.text_input("Largura (m; opcional)");alt=d3.text_input("Altura (m; opcional)")
            if st.form_submit_button("Adicionar carga"):
                try:

                    new={"id":nova_id(),"nome":nome,"categoria":categoria,"massa_kg":numero_digitado(massastr),
                        "x_m":numero_digitado(xstr) if xstr else None,
                        "y_m":numero_digitado(ystr) if ystr else None,
                        "z_m":numero_digitado(zstr) if zstr else None,
                        "comp_m":numero_digitado(comp) if comp else None,"larg_m":numero_digitado(larg) if larg else None,"alt_m":numero_digitado(alt) if alt else None,
                        "posicao_sugerida":False}
                    if sugerir:
                        propor_posicoes([*st.session_state.cargas,new],barco)
                    verificar_carga(new,st.session_state.barco)
                    cargas=copy.deepcopy(st.session_state.cargas)+[new]
                    aplicar(novas_cargas=cargas,descricao="Adicionar "+nome)
                    st.success("Carga adicionada")
                except Exception as e:st.error(str(e))
    if st.session_state.cargas:
        with painel_planta.container():
            st.subheader("Distribuição das cargas na planta")
            sugeridas=[c["nome"]+" ("+c["eixos_sugeridos"]+")" for c in st.session_state.cargas if c.get("eixos_sugeridos")]
            if sugeridas:
                st.caption("Coordenadas sugeridas na montagem inicial · "+", ".join(sugeridas))
            st.caption("Arraste uma carga e solte na posição desejada. Massa e altura são preservadas. Use Desfazer para recuperar a posição anterior.")
            planta_editavel(barco,st.session_state.cargas,"cadastro")
        st.subheader("Editar massas, posições e dimensões")
        df=pd.DataFrame(st.session_state.cargas,columns=COLUNAS_CARGAS)
        edit=st.data_editor(df,num_rows="fixed",disabled=["id"],width="stretch",key=f"edit_cargas_{st.session_state.revisao_cargas}")
        salvar, selecionar, duplicar=st.columns(3)
        if salvar.button("Aplicar alterações na tabela"):
            try:
                anteriores={r["id"]:r for r in st.session_state.cargas}
                cargas=[{**anteriores[r["id"]],**r} for r in edit.to_dict("records")]
                for c in cargas:
                    for k in ("massa_kg","x_m","y_m","z_m","comp_m","larg_m","alt_m"):
                        if pd.isna(c.get(k)):c[k]=None
                    verificar_carga(c,st.session_state.barco)
                aplicar(novas_cargas=cargas,descricao="Editar cargas")
                st.success("Atualizado")
            except Exception as e:st.error(str(e))
        nomeescolhido=selecionar_carga("Selecione uma carga",st.session_state.cargas,selecionar)
        if duplicar.button("Duplicar carga selecionada"):
            cargas=copy.deepcopy(st.session_state.cargas)
            item=next(c for c in cargas if c["id"]==nomeescolhido).copy()
            item["id"]=nova_id();item["nome"]+=" (cópia)"
            cargas.append(item)
            aplicar(novas_cargas=cargas,descricao="Duplicar carga")
            st.toast("Carga duplicada")
            st.rerun()
        if st.button("Remover carga selecionada"):
            aplicar(novas_cargas=[c for c in st.session_state.cargas if c["id"]!=nomeescolhido],descricao="Remover carga")
            st.toast("Carga removida")
            st.rerun()
    buttons=st.columns(4)
    if buttons[0].button("Desfazer",disabled=not st.session_state.undo):historico("undo");st.rerun()
    if buttons[1].button("Refazer",disabled=not st.session_state.redo):historico("redo");st.rerun()
    if buttons[2].button("Salvar condição inicial"):
        st.session_state.cargas_inicio=copy.deepcopy(st.session_state.cargas);st.success("Condição inicial armazenada")
    if buttons[3].button("Restaurar condição inicial",disabled=st.session_state.cargas_inicio is None):
        restaurar_cargas();st.rerun()
    try:
        cond=calcular(st.session_state.barco,st.session_state.cargas)
        a,b,c,d=st.columns(4)
        a.metric("Δ (kg)",f"{cond['deslocamento_kg']:.3f}")
        b.metric("LCG (m)","—" if cond["lcg_m"] is None else f"{cond['lcg_m']:.4f}")
        c.metric("TCG (m)","—" if cond["tcg_m"] is None else f"{cond['tcg_m']:.4f}")
        d.metric("KG (m)","—" if cond["kg_m"] is None else f"{cond['kg_m']:.4f}")
        if not barco.get("L_m") or not barco.get("B_m"):
            st.plotly_chart(planta(barco,st.session_state.cargas,cond),width="stretch")
        st.dataframe(pd.DataFrame([{"Eixo":k,"Momento total (kg·m)":cond["momento_"+k.lower()+"_m"]} for k in ("X","Y","Z")]), hide_index=True)
        if st.session_state.cargas:
            quadro=pd.DataFrame(st.session_state.cargas)
            st.dataframe(quadro.groupby("categoria")["massa_kg"].sum().reset_index(name="Massa por categoria (kg)"),hide_index=True)
        try:
            h=consultar(st.session_state.barco,cond["deslocamento_kg"])
            st.plotly_chart(perfil({**st.session_state.barco,"calado_m":h.get("calado_m")},st.session_state.cargas,cond),width="stretch")
            e=avaliar(st.session_state.barco,cond,h); tr=trim_estatico(cond,h)
            with st.expander("Detalhes da condição hidrostática"):
                st.write(h["metodo"])
                st.dataframe(pd.DataFrame([{"Parâmetro":k, "Valor":v} for k,v in {**h,**e,**tr}.items() if k != "metodo"]), hide_index=True, width="stretch")
        except ValueError as ex:st.warning(f"Sem estado hidrostático aplicável: {ex}")
        if st.session_state.barco.get("gz_curva"):
            import plotly.express as px
            try:
                gz=gz_adaptada(st.session_state.barco,cond)
                st.plotly_chart(px.line(pd.DataFrame(gz),x="angulo_graus",y="gz_m",title="GZ adaptada ao KG (mesmo deslocamento, TCG=0, FSM=0)"),width="stretch")
            except ValueError as ex:st.info("Curva GZ não adaptada: "+str(ex))
    except ValueError as ex:st.warning(str(ex))
    st.download_button("Exportar cargas CSV",csv_bytes(st.session_state.cargas,COLUNAS_CARGAS),file_name="cargas.csv")


render()

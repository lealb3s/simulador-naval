"""Aliases físicos EXATOS (não fuzzy): exige confirmação de unidade na tela."""
import re
import unicodedata


def simplificar(texto):
    v=unicodedata.normalize('NFKD',str(texto))
    v=''.join(c for c in v if not unicodedata.combining(c)).lower()
    return re.sub(r'\s+',' ',v).strip()

_HIDRO={
 'deslocamento_kg':('deslocamento_kg','delta (deslocamento) [t]','delta (deslocamento) [kg]',
    'deslocamento [t]','deslocamento [kg]','deslocamento (t)','deslocamento (kg)','delta [t]','delta [kg]'),
 'calado_m':('calado_m','t moldado [m]','calado [m]','calado (m)','calado moldado [m]'),
 'km_m':('km_m','km_t [m]','kmt [m]','km transversal [m]','km transv. [m]'),
 'kb_m':('kb_m','kb = vcb [m]','kb [m]','vcb [m]'),
 'lcb_m':('lcb_m','lcb [m]'), 'lcf_m':('lcf_m','lcf [m]'),
 'mtc_kgm_por_m':('mtc_kgm_por_m',),
}
_GZ={'angulo_graus':('angulo_graus','angulo [graus]','angulo (graus)','angulo [°]','heel [deg]'),
     'gz_m':('gz_m','gz [m]','gz (m)','gz [mm]')}
_CASCO={'x_m':('x_m','x [m]','x (m)'), 'y_m':('y_m','y [m]','y (m)')}
_CARGAS={
 'id':('id','identificador','codigo'), 'nome':('nome','carga','item'),
 'categoria':('categoria','tipo de carga'),
 'massa_kg':('massa_kg','massa [kg]','massa (kg)','peso [kg]','massa [t]','massa (t)'),
 'x_m':('x_m','x [m]','lcg [m]','posicao longitudinal [m]'),
 'y_m':('y_m','y [m]','tcg [m]','posicao transversal [m]'),
 'z_m':('z_m','z [m]','kg [m]','altura cg [m]'),
 'comp_m':('comp_m','comprimento carga [m]'), 'larg_m':('larg_m','largura carga [m]'),
 'alt_m':('alt_m','altura carga [m]'),
}
_LEITURAS={
 'momento_kgm':('momento_kgm','momento [kg.m]','momento [kg·m]', 'momento [kgm]'),
 'tangente':('tangente','tan theta','tan θ','tan(θ)','tan(theta)'),
 'estavel':('estavel','estabilizada','estável'), 'fonte':('fonte','origem'),
}
_GLOBAL={
 'deslocamento_kg':_HIDRO['deslocamento_kg']+('deslocamento','delta','Δ','massa total [kg]'),
 'lcg_m':('lcg_m','lcg','lcg [m]'), 'tcg_m':('tcg_m','tcg','tcg [m]'), 'kg_m':('kg_m','kg','kg [m]','vcg [m]'),
}
MAPA={'global':_GLOBAL,'hidro':_HIDRO,'gz':_GZ,'casco':_CASCO,'cargas':_CARGAS,'leituras':_LEITURAS}


def sugestao_coluna(tipo,campo,cabecalhos):
    validos={simplificar(x) for x in MAPA.get(tipo,{}).get(campo,(campo,))}
    matches=[h for h in cabecalhos if simplificar(h) in validos]
    return matches[0] if len(matches)==1 else None


def identificar_tipo_tabela(cabecalhos):
    cabecalhos=list(cabecalhos or [])
    if not cabecalhos:return None
    sc={simplificar(h) for h in cabecalhos}
    if ('campo' in sc or 'grandeza' in sc or 'parametro' in sc) and 'valor' in sc:
        return 'barco'
    for t,mandatory in [('hidro',('deslocamento_kg','calado_m','km_m')),
                        ('gz',('angulo_graus','gz_m')),
                        ('global',('deslocamento_kg','lcg_m','tcg_m','kg_m')),
                        ('cargas',('massa_kg','x_m','y_m','z_m')),
                        ('leituras',('momento_kgm','tangente')),
                        ('casco',('x_m','y_m'))]:
        if all(sugestao_coluna(t,x,cabecalhos) is not None for x in mandatory):return t
    return None

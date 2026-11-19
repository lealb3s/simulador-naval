"""
hydro_core.py - Núcleo de cálculo hidrostático do VLCC 320K (sem dependência do Streamlit).

Convenções
----------
* x  : distância longitudinal a partir da AP (popa) [m], positivo para vante.
* z  : altura acima da linha de base (Bottom Line) [m].
* y  : meia-boca [m] (tabela de offsets em mm -> dividida por 1000).
* "Calado" da tabela de saída = calado EXTREMO (como na tabela de referência do PDF:
  calado moldado = calado extremo - espessura da chapa de quilha, ex.: 14.983 <-> 15.000).
* LCB/LCF são reportados a partir de MEIA-NAU (+ a vante), como na tabela de referência.
"""
import numpy as np
import pandas as pd

# ------------------------------------------------------------------ dados de entrada
LBP, B, D, TD = 320.0, 60.0, 30.0, 20.0     # dimensões principais [m]
KEEL_T = 0.017                               # espessura da chapa de quilha [m]
RHO = 1.025                                  # densidade da água do mar [t/m3]
DRAFTS = list(range(0, 19)) + [20, 22, 24, 26, 28, 30]   # calados pedidos [m]

# Estações em "unidades de estação" (1 un = LBP/20 = 16 m). AP = 0, FP = 20.
STATIONS = np.array([-0.333, -0.166, 0, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
                     15, 16, 17, 18, 18.5, 19, 19.5, 20, 20.43])
# Linhas d'água [m]; 0 = Bottom Line
WL = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24, 26, 28, 30], float)

_F = [30000] * 23
HB_MM = np.array([
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2468,5714,7779,9170,10121,10756,11004],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4375,7391,9426,10762,11695,12342,12624],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1063,6079,9047,11017,12341,13189,13760,14172],
 [0,0,0,0,0,764,816,0,0,0,0,0,0,168,1837,4321,6952,10875,13560,15298,16576,17417,17959,18398],
 [0,2406,3206,3565,3678,3619,3402,3131,2968,3001,3252,3827,4814,6329,8317,10380,12274,15329,17636,19272,20392,21158,21671,22002],
 [1980,6807,8190,9059,9678,10145,10541,10954,11466,12154,13093,14276,15597,16949,18245,19424,20493,22378,23898,25016,25802,26361,26692,26880],
 [6384,11580,13364,14648,15724,16688,17598,18500,19402,20311,21228,22144,23039,23885,24666,25372,26001,27044,27847,28406,28760,28996,29154,29256],
 [11520,16453,18528,20045,21296,22410,23415,24310,25106,25826,26471,27039,27541,27979,28357,28679,28953,29381,29669,29822,29894,29940,29979,30000],
 [16608,21227,23138,24564,25705,26633,27391,28007,28502,28896,29207,29450,29636,29775,29875,29944,29984,30000,30000,30000,30000,30000,30000,30000],
 [21264,25255,26779,27784,28512,29058,29454,29723,29891,29978]+[30000]*14,
 [24816,27985,28981,29547,29861,29990]+[30000]*18,
 [26736,29221,29818,29997]+[30000]*20,
 [27400]+_F, [27400]+_F, [27400]+_F, [27400]+_F, [27400]+_F, [27400]+_F,
 [27400,29449,29930]+[30000]*21,
 [25788,28535,29419,29851,29975]+[30000]*19,
 [21972,26146,27478,28336,28935,29340,29586,29706,29754]+[29760]*15,
 [15192,21267,23221,24483,25393,26105,26632,26983,27227,27368,27389,27362,27359,27361,27359,27360,27360,27360,27360,27360,27371,27459,27619,27852],
 [10644,17313,19482,20938,22038,22879,23521,23994,24314,24542,24696,24786,24815,24817,24815,24816,24816,24816,24816,24861,25029,25297,25641,26040],
 [5880,12220,14539,16152,17372,18277,19013,19626,20082,20421,20667,20831,20916,20934,20899,20832,20772,20755,20868,21132,21485,21945,22541,23280],
 [1860,6613,8767,10271,11400,12291,13009,13589,14048,14398,14640,14775,14812,14760,14627,14460,14348,14347,14640,15180,15908,16798,17821,18960],
 [0,1875,3102,4014,4751,5371,5883,6295,6615,6850,7005,7067,7023,6868,6600,6190,5568,3172,0,1872,5178,8178,10707,12960],
 [0,0,0,0,0,0,326,562,678,754,800,822,817,741,524,0,0,0,0,0,0,0,0,3192],
], dtype=float)
assert HB_MM.shape == (len(STATIONS), len(WL)), HB_MM.shape


# ------------------------------------------------------------------ Passo 1: modificar a tabela
def build_offsets(hb_mm=HB_MM, stations=STATIONS):
    """Converte mm->m e INSERE a estação 20.215 (ponto médio entre 20.0 e 20.43) por
    interpolação linear, para que o último trecho possa usar Simpson 1a regra (Step 1/2 do PDF)."""
    hb = hb_mm / 1000.0                                   # mm -> m
    i = int(np.where(stations == 20)[0][0])
    mid = 0.5 * (hb[i] + hb[i + 1])                       # interpolação linear
    st = np.insert(stations, i + 1, 20.215)
    return st, np.insert(hb, i + 1, mid, axis=0)


ST, HB = build_offsets()
X = ST * LBP / 20.0                                       # posição x [m] de cada estação

# Plano de integração longitudinal (Step 2 do PDF): (est. inicial, est. final, regra)
# S1 = Simpson 1a regra (3 ordenadas), S2 = Simpson 2a regra (4 ordenadas).
LONG_SEGMENTS = [(-0.333, 0, "S1"), (0, 1, "S1"),
                 (1, 4, "S2"), (4, 7, "S2"), (7, 10, "S2"), (10, 13, "S2"), (13, 16, "S2"),
                 (16, 18, "S1"), (18, 19, "S1"), (19, 20, "S1"), (20, 20.43, "S1")]


def _idx(st):
    return int(np.argmin(np.abs(ST - st)))


def long_integrate(f):
    """Integra, ao longo de x [m], a função tabelada f (um valor por estação de ST),
    segundo LONG_SEGMENTS.
      S1: Área = (s/3)(y0 + 4 y1 + y2)          (s = espaçamento)
      S2: Área = (3s/8)(y0 + 3 y1 + 3 y2 + y3)
    Para 20.0–20.43 o ponto médio é a estação interpolada 20.215."""
    total = 0.0
    for a, b, rule in LONG_SEGMENTS:
        ia, ib = _idx(a), _idx(b)
        if rule == "S1":
            im = _idx((a + b) / 2) if abs((a + b) / 2 - ST[_idx((a + b) / 2)]) < 1e-6 else None
            if (a, b) == (-0.333, 0):                  # meio = -0.166 (≈ -0.1665)
                im = _idx(-0.166)
            if (a, b) == (0, 1):                       # 0, 0.5, 1.0
                im = _idx(0.5)
            if (a, b) in [(16, 18), (18, 19), (19, 20)]:
                im = _idx((a + b) / 2)
            if (a, b) == (20, 20.43):
                im = _idx(20.215)
            s = (X[ib] - X[ia]) / 2.0
            total += s / 3.0 * (f[ia] + 4 * f[im] + f[ib])
        else:                                          # S2: 4 pontos igualmente espaçados
            idx = [_idx(a + k * (b - a) / 3) for k in range(4)]
            s = (X[ib] - X[ia]) / 3.0
            total += 3 * s / 8.0 * (f[idx[0]] + 3 * f[idx[1]] + 3 * f[idx[2]] + f[idx[3]])
    return total


def vert_integrate(z, y):
    """Simpson composto em z (nós não necessariamente uniformes).
    Usa S1 (2 intervalos iguais), S2 (3 intervalos iguais) e, se sobrar um intervalo
    de largura diferente (ex.: calado fracionário 14.983), a regra do trapézio —
    exata para a interpolação linear adotada entre linhas d'água."""
    z, y = np.asarray(z, float), np.asarray(y, float)
    n, i, tot = len(z), 0, 0.0
    h = np.diff(z)
    while i < n - 1:
        if i + 2 < n and np.isclose(h[i], h[i + 1]):          # Simpson 1a regra
            tot += h[i] / 3 * (y[i] + 4 * y[i + 1] + y[i + 2]); i += 2
        elif i + 3 < n and np.isclose(h[i], h[i + 1]) and np.isclose(h[i + 1], h[i + 2]):
            tot += 3 * h[i] / 8 * (y[i] + 3 * y[i + 1] + 3 * y[i + 2] + y[i + 3]); i += 3
        else:                                                  # trapézio (1 intervalo)
            tot += h[i] / 2 * (y[i] + y[i + 1]); i += 1
    return tot


def z_nodes(T):
    """Nós verticais: linhas d'água da tabela abaixo de T + o próprio T (interpolação linear)."""
    return np.append(WL[WL < T - 1e-9], T) if T > 0 else np.array([0.0])


def hb_at(T):
    """Meia-boca de TODAS as estações no calado T (interp. linear entre linhas d'água)."""
    return np.array([np.interp(T, WL, HB[i]) for i in range(len(ST))])


def station_quantities(T):
    """Passo 4: para cada estação, em calado moldado T, devolve
       A  = 2∫y dz       área seccional (boca inteira) [m2]
       M  = 2∫y z dz     1o momento da seção em relação à base [m3]
       G  = girth molhado da seção [m]  (fundo plano + 2 lados)"""
    zs = z_nodes(T)
    A, M, G = np.zeros(len(ST)), np.zeros(len(ST)), np.zeros(len(ST))
    if T <= 0:
        return A, M, G
    for i in range(len(ST)):
        y = np.array([np.interp(z, WL, HB[i]) for z in zs])
        A[i] = 2 * vert_integrate(zs, y)
        M[i] = 2 * vert_integrate(zs, y * zs)
        G[i] = 2 * y[0] + 2 * np.sum(np.hypot(np.diff(y), np.diff(zs)))   # comprimento do contorno
    return A, M, G


def hydrostatics_moulded(T):
    """Calcula todas as propriedades hidrostáticas para o calado MOLDADO T."""
    r = dict(T_mld=T)
    if T <= 0:
        return {k: 0.0 for k in ["V", "LCB", "LCF", "VCB", "BMt", "KMt", "BMl", "KMl",
                                 "MTC", "TPC", "Awp", "WSA", "CB", "CWP", "CM", "CP"]} | r
    A, M, G = station_quantities(T)
    y = hb_at(T)                                   # meia-boca da linha d'água T
    V = long_integrate(A)                          # V = ∫A dx
    LCB_ap = long_integrate(A * X) / V             # LCB = ∫A x dx / V (desde a AP)
    VCB = long_integrate(M) / V                    # KB = ∫(∫2 y z dz) dx / V
    Awp = long_integrate(2 * y)                    # Awp = ∫2y dx
    LCF_ap = long_integrate(2 * y * X) / Awp       # LCF = ∫2 y x dx / Awp
    It = long_integrate(2.0 / 3.0 * y ** 3)        # It = ∫(2/3) y³ dx   (em torno da LC)
    IL_ap = long_integrate(2 * y * X ** 2)         # I em torno da AP
    IL = IL_ap - Awp * LCF_ap ** 2                 # Steiner: I em torno do LCF
    BMt, BMl = It / V, IL / V                      # BM = I / V
    WSA = long_integrate(G)                        # área molhada ≈ ∫ girth dx
    Am = A[_idx(10)]                               # seção a meia-nau (estação 10)
    r.update(V=V, LCB=LCB_ap - LBP / 2, LCF=LCF_ap - LBP / 2, VCB=VCB,
             BMt=BMt, KMt=VCB + BMt, BMl=BMl, KMl=VCB + BMl,
             MTC=RHO * IL / (100 * LBP),            # t·m/cm  (MTC = ρ I_L / (100 L))
             TPC=RHO * Awp / 100,                   # t/cm    (TPC = ρ Awp / 100)
             Awp=Awp, WSA=WSA,
             CB=V / (LBP * B * T), CWP=Awp / (LBP * B),
             CM=Am / (B * T), CP=V / (Am * LBP))
    return r


def hydrostatic_table(drafts=DRAFTS, keel=KEEL_T, rho=RHO):
    """Tabela hidrostática completa. 'Calado' = calado extremo; moldado = extremo - keel."""
    rows = []
    for Te in drafts:
        Tm = max(Te - keel, 0.0)
        h = hydrostatics_moulded(Tm)
        Vext = h["V"] + h["WSA"] * keel if Te > 0 else 0.0   # + volume das chapas (WSA × espessura)
        rows.append({
            "Draft_ext (m)": Te, "Draft_mld (m)": round(Tm, 3),
            "Volume_mld (m3)": h["V"], "Volume_ext (m3)": Vext,
            "Displ_mld (t)": rho * h["V"], "Displ_ext (t)": rho * Vext,
            "LCB (m)": h["LCB"], "LCF (m)": h["LCF"], "VCB=KB (m)": h["VCB"],
            "BMt (m)": h["BMt"], "KMt (m)": h["KMt"], "BMl (m)": h["BMl"], "KMl (m)": h["KMl"],
            "MTC (t.m/cm)": h["MTC"], "TPC (t/cm)": h["TPC"], "Awp (m2)": h["Awp"],
            "WSA (m2)": h["WSA"], "CB": h["CB"], "CWP": h["CWP"], "CM": h["CM"], "CP": h["CP"]})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ referência (PDF, p.4)
REF_DRAFT_EXT = [15, 16, 17, 18, 19, 20, 21, 22]
REF = pd.DataFrame({
 "Draft_ext (m)": REF_DRAFT_EXT,
 "Volume_mld (m3)": [235335.3, 252293.8, 269404.3, 286658.7, 304044.4, 321546.8, 339154.3, 356853.1],
 "Displ_ext (t)": [241596.7, 258991.0, 276541.2, 294378.8, 312070.8, 330022.1, 348081.0, 366233.3],
 "Volume_ext (m3)": [235704.1, 252674.2, 269796.3, 287062.4, 304459.3, 321972.8, 339591.2, 357300.8],
 "LCF (m)": [7.680, 6.094, 4.477, 3.015, 1.888, 1.018, 0.365, -0.100],
 "LCB (m)": [13.790, 13.327, 12.816, 12.268, 11.705, 11.146, 10.602, 10.083],
 "VCB=KB (m)": [7.727, 8.249, 8.772, 9.296, 9.822, 10.347, 10.874, 11.400],
 "TPC (t/cm)": [173.0, 174.6, 176.1, 177.6, 178.8, 180.0, 181.0, 181.8],
 "MTC (t.m/cm)": [3699.8, 3801.8, 3902.6, 3996.3, 4077.4, 4150.3, 4214.6, 4271.6],
 "KMt (m)": [27.100, 26.484, 26.006, 25.642, 25.368, 25.171, 25.032, 24.945],
 "KMl (m)": [497.777, 477.985, 460.362, 443.913, 427.922, 412.771, 398.330, 384.639],
 "Awp (m2)": [16882.6, 17034.8, 17183.7, 17322.8, 17445.8, 17557.2, 17655.2, 17741.4],
 "WSA (m2)": [24585.0, 25357.5, 26137.6, 26910.5, 27661.0, 28398.1, 29126.0, 29847.8],
 "CB": [0.8181, 0.8221, 0.8262, 0.8302, 0.8342, 0.8381, 0.8418, 0.8455],
 "CP": [0.8208, 0.8247, 0.8286, 0.8325, 0.8364, 0.8401, 0.8438, 0.8474],
 "CWP": [0.8793, 0.8872, 0.8950, 0.9022, 0.9086, 0.9144, 0.9195, 0.9240],
 "CM": [0.9967, 0.9969, 0.9971, 0.9973, 0.9974, 0.9975, 0.9977, 0.9978]})


def validate():
    """Recalcula nos calados da referência (15–22 m extremos, inclui 19 e 21 que não estão na
    lista principal) e compara com a tabela do PDF. Retorna (calculado, referência, erro %)."""
    df = hydrostatic_table(REF_DRAFT_EXT)
    calc = df.set_index("Draft_ext (m)")[list(REF.columns[1:])]
    ref = REF.set_index("Draft_ext (m)")
    err = (calc - ref) / ref.abs() * 100
    return calc, ref, err


# ------------------------------------------------------------------ linhas de forma
def body_plan(ax, stations_to_plot=None):
    """Plano de balizas: seções (y×z). Ré (estações 0–10) à esquerda, vante (10–20) à direita."""
    for i, s in enumerate(ST):
        if s < 0 or (stations_to_plot is not None and s not in stations_to_plot):
            continue
        y = np.concatenate([[HB[i][0]], HB[i]])
        z = np.concatenate([[0], WL])
        sign = -1 if s <= 10 else 1
        ax.plot(sign * y, z, lw=0.8, color="tab:blue" if sign < 0 else "tab:red")
    ax.axhline(TD, ls="--", c="k", lw=0.6); ax.axvline(0, c="gray", lw=0.5)
    ax.set_xlabel("Meia-boca y [m]  (ré ← | → vante)"); ax.set_ylabel("z [m]")
    ax.set_title("Plano de balizas"); ax.set_aspect("equal"); ax.grid(alpha=.3)


def half_breadth_plan(ax):
    """Plano de linhas d'água: y(x) para cada linha d'água."""
    for j, w in enumerate(WL):
        ax.plot(X, HB[:, j], lw=0.8, label=f"{w:g}" if w in (0, 10, 20, 30) else None)
    for xs in X[(ST >= 0) & (ST <= 20) & (ST == np.round(ST))]:
        ax.axvline(xs, c="gray", lw=0.3)
    ax.set_xlabel("x desde AP [m]"); ax.set_ylabel("y [m]")
    ax.set_title("Linhas d'água (plano de meias-bocas)"); ax.grid(alpha=.3); ax.legend(title="WL [m]")


def profile(ax):
    """Perfil: contorno de proa/popa (extensão longitudinal com y>0 em cada linha d'água)."""
    xmin, xmax = [], []
    for j in range(len(WL)):
        pos = np.where(HB[:, j] > 1e-6)[0]
        if len(pos):
            i0, i1 = pos[0], pos[-1]
            xmin.append(X[i0]); xmax.append(X[i1])
        else:
            xmin.append(np.nan); xmax.append(np.nan)
    ax.plot(xmin, WL, "k"); ax.plot(xmax, WL, "k")
    ax.plot([xmin[0], xmax[0]], [WL[0], WL[0]], "k")          # linha de quilha (z = 0)
    ax.plot([xmin[-1], xmax[-1]], [WL[-1], WL[-1]], "k")      # convés (z = 30)
    for w in WL:
        ax.axhline(w, c="lightgray", lw=0.3)
    for xs in X[(ST >= 0) & (ST <= 20) & (ST == np.round(ST))]:
        ax.axvline(xs, c="lightgray", lw=0.3)
    ax.axhline(TD, ls="--", c="b", lw=0.8, label=f"Td = {TD:g} m"); ax.legend()
    ax.set_xlabel("x desde AP [m]"); ax.set_ylabel("z [m]"); ax.set_title("Vista de perfil")
    ax.set_aspect("equal"); ax.grid(False)

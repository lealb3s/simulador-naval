"""
incl_core.py - Física e estatística da prova de inclinação (sem Streamlit).

Hipóteses
---------
* Convenção: φ > 0 = inclinação para BORESTE (vista de ré); M > 0 = peso deslocado para boreste.
* Equilíbrio "verdadeiro":  Δ·[GZ(φ) − FSC·sinφ] + k_moor·φ[°] = M·cosφ    (GZ da AP1.3, não-linear)
* Aproximação metacêntrica usada no processamento:  tanφ = M / (Δ·GM)   ->  GM = M / (Δ·tanφ)
* Pêndulo: δ = L·tanφ  ->  φ = atan(δ/L).
* Transitório de balanço: φ(t) = φ_eq + Δφ·e^(−ζωt)·cos(ω_d t),  ω = sqrt(g·GM)/(k_roll·B).
"""
import numpy as np, pandas as pd
from dataclasses import dataclass, field, replace
G = 9.81


def make_gz(GM, BM, T, B, D):
    """Curva GZ de parede lateral: GZ = sinφ (GM + ½ BM tan²φ), com decaimento após a entrada do convés na água."""
    deg = np.array([0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 35, 40, 45, 50, 60.])
    p = np.radians(deg); gz = np.sin(p) * (GM + 0.5 * BM * np.tan(p) ** 2)
    de = np.degrees(np.arctan(2 * (D - T) / B))          # ângulo de imersão do convés
    g_de = np.interp(de, deg, gz)
    gz = np.where(deg <= de, gz, np.interp(deg, [de, 90], [g_de, 0]))
    return deg, gz


@dataclass
class Ship:
    disp: float = 123800.0      # deslocamento [t]
    draft: float = 8.0          # calado do ensaio [m]
    KM: float = 39.5            # KM transversal [m]
    KG: float = 16.0            # KG de referência [m]
    BM: float = 34.4            # BMt [m] (só para gerar a curva GZ padrão)
    B: float = 60.0
    D: float = 30.0
    k_roll: float = 0.35        # raio de giração de balanço / B
    zeta: float = 0.05          # razão de amortecimento do balanço
    gz_deg: tuple = None
    gz_m: tuple = None

    def __post_init__(self):
        if self.gz_deg is None:
            d, g = make_gz(self.KM - self.KG, self.BM, self.draft, self.B, self.D)
            self.gz_deg, self.gz_m = tuple(d), tuple(g)


def gz_of(ship, phi_rad):
    p = np.asarray(phi_rad, float)
    return np.sign(p) * np.interp(np.abs(np.degrees(p)), ship.gz_deg, ship.gz_m)


def gm_curve(ship):
    """GM implícito na curva GZ (inclinação em 0,5°)."""
    return float(np.interp(0.5, ship.gz_deg, ship.gz_m) / np.radians(0.5))


def equilibrium(ship, M, fsc=0.0, k_moor=0.0):
    """Ângulo de equilíbrio [rad] para momento M [t·m] (bisseção vetorizada, f é crescente em φ)."""
    M = np.atleast_1d(np.asarray(M, float)); lo = np.full_like(M, -0.5); hi = np.full_like(M, 0.5)
    for _ in range(50):
        mid = (lo + hi) / 2
        f = ship.disp * (gz_of(ship, mid) - fsc * np.sin(mid)) + k_moor * np.degrees(mid) - M * np.cos(mid)
        hi = np.where(f > 0, mid, hi); lo = np.where(f > 0, lo, mid)
    return (lo + hi) / 2


@dataclass
class Plan:
    n_g: int = 2                 # nº de pesos por grupo (grupos A e B)
    m_w: float = 100.0           # massa de cada peso [t]
    d: float = 20.0              # distância transversal de movimentação [m]
    pend: list = field(default_factory=lambda: [(12.0, 1.0), (18.0, 1.0)])   # (comprimento m, resolução mm)
    seq: list = None
    def __post_init__(self):
        if self.seq is None: self.seq = default_seq(self.d)


def default_seq(d):
    """9 leituras: posição inicial, 3 passos p/ boreste, retorno ao zero, 3 passos p/ bombordo, zero final.
    (yA, yB) = posição transversal [m] dos grupos A e B (+ = boreste)."""
    return [(0, 0), (d, 0), (d, d), (0, d), (0, 0), (-d, 0), (-d, -d), (0, -d), (0, 0)]


@dataclass
class Err:
    mass_pct: float = 0.0; dist_pct: float = 0.0
    len_pct: list = field(default_factory=lambda: [0., 0., 0.])        # comprimento real ≠ declarado
    ref_shift_mm: list = field(default_factory=lambda: [0., 0., 0.]); ref_shift_from: int = 99
    gross_mm: float = 0.0; gross_idx: int = 3; gross_pend: int = 0
    noise_mm: float = 0.0
    wind_sigma: float = 0.0; wind_bias: float = 0.0                    # [°]
    tank_l: float = 0.0; tank_b: float = 0.0; tank_fill: float = 0.0; tank_rho: float = 1.0
    fsc_declared: bool = False
    k_moor: float = 0.0                                                # [t·m/°]
    disp_pct: float = 0.0; km_err: float = 0.0                         # erro de calado/densidade -> Δ e KM adotados


def fsc_of(err, ship):
    """Correção de superfície livre: FSC = ρ_t·i/Δ,  i = l·b³/12."""
    if 0 < err.tank_fill < 1 and err.tank_l > 0:
        return err.tank_rho * err.tank_l * err.tank_b ** 3 / 12 / ship.disp
    return 0.0


def phi_series(ship, plan, err):
    y = np.array(plan.seq, float).sum(1)
    Mnom = plan.n_g * plan.m_w * y
    Mreal = plan.n_g * plan.m_w * (1 + err.mass_pct / 100) * y * (1 + err.dist_pct / 100)
    return Mnom, Mreal, np.degrees(equilibrium(ship, Mreal, fsc_of(err, ship), err.k_moor))


def omega_n(ship, err):
    return np.sqrt(G * (gm_curve(ship) - fsc_of(err, ship))) / (ship.k_roll * ship.B)


def min_wait(ship, err, dphi, tol=0.01):
    """Tempo [s] para a amplitude residual cair abaixo de tol [°]."""
    a = abs(dphi)
    return 0.0 if a <= tol else float(np.log(a / tol) / (ship.zeta * omega_n(ship, err)))


def reading_from_M(ship, pend, err, j, Mnom, Mreal, phi_prev, tw, rng, tol=0.01):
    """Leitura para um momento ARBITRÁRIO (pesos colocados livremente pelo usuário).
    Mnom = momento declarado (usado no processamento); Mreal = momento físico (com erros de massa/distância).
    phi_prev = equilíbrio anterior [°]; tw = tempo de espera [s].  Retorna (linha, amplitude residual, φ_eq)."""
    peq = float(np.degrees(equilibrium(ship, Mreal, fsc_of(err, ship), err.k_moor))[0])
    dphi = peq - phi_prev
    wn, z = omega_n(ship, err), ship.zeta
    env = abs(dphi) * np.exp(-z * wn * tw) / np.sqrt(1 - z ** 2)                    # envelope do transitório
    trans = -dphi * np.exp(-z * wn * tw) * np.cos(wn * np.sqrt(1 - z ** 2) * tw)   # resposta ao degrau: parte de φ_antigo
    phi = peq + trans + rng.normal(0, err.wind_sigma) + err.wind_bias
    row = dict(leitura=j, M_nom=Mnom, M_real=Mreal, phi_eq=peq, phi_real=phi, t_espera=tw, amp_residual=env)
    tans = []
    for k, (L, res) in enumerate(pend):
        Lr = L * (1 + err.len_pct[k] / 100)
        d = Lr * np.tan(np.radians(phi)) * 1000                        # deflexão [mm]
        if j >= err.ref_shift_from: d += err.ref_shift_mm[k]
        if err.gross_mm and j == err.gross_idx and k == err.gross_pend: d += err.gross_mm
        d += rng.normal(0, err.noise_mm)
        dr = np.round(d / res) * res                                   # resolução da leitura
        row[f"d{k+1}_mm"] = dr; row[f"tan{k+1}"] = dr / 1000 / L       # tanφ com L DECLARADO
        row[f"phi{k+1}_deg"] = np.degrees(np.arctan(row[f"tan{k+1}"])); tans.append(row[f"tan{k+1}"])
    row["tan_med"] = float(np.mean(tans)); row["phi_est"] = float(np.degrees(np.arctan(row["tan_med"])))
    return row, env, peq


def reading(ship, plan, err, j, tw, rng, tol=0.01):
    """Leitura j da sequência planejada (plan.seq). Retorna (linha, amplitude residual)."""
    Mnom, Mreal, peq = phi_series(ship, plan, err)
    row, env, _ = reading_from_M(ship, plan.pend, err, j, Mnom[j], Mreal[j], peq[j - 1] if j > 0 else peq[0], tw, rng, tol)
    row.update(yA=plan.seq[j][0], yB=plan.seq[j][1])
    return row, env


def simulate_test(ship, plan, err, seed=0, tol=0.01, margin=5.0):
    """Prova completa automática: espera o mínimo necessário (+margin s) antes de cada leitura."""
    rng = np.random.default_rng(seed); _, _, peq = phi_series(ship, plan, err); rows = []
    for j in range(len(plan.seq)):
        dphi = peq[j] - (peq[j - 1] if j > 0 else peq[0])
        rows.append(reading(ship, plan, err, j, min_wait(ship, err, dphi, tol) + margin, rng, tol)[0])
    return pd.DataFrame(rows)


def fit_line(x, y, origin=False):
    x, y = np.asarray(x, float), np.asarray(y, float); n = len(x)
    A = x[:, None] if origin else np.c_[x, np.ones(n)]
    c, *_ = np.linalg.lstsq(A, y, rcond=None); r = y - A @ c
    dof = max(n - A.shape[1], 1); s2 = (r @ r) / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    sst = ((y - y.mean()) ** 2).sum()
    return dict(slope=c[0], icpt=0.0 if origin else c[1], se=float(np.sqrt(cov[0, 0])), resid=r,
                r2=1 - (r @ r) / sst if sst > 0 else np.nan, rms=float(np.sqrt(s2)))


def process(df, ship, disp_adopt=None, km_adopt=None, fsc_corr=0.0, origin=False):
    """GM = 1/(slope·Δ);  KG = KM − GM − FSC_corrigida. Ajusta cada pêndulo e a média."""
    disp = disp_adopt or ship.disp; km = km_adopt or ship.KM; out = {}
    cols = [c for c in df.columns if c.startswith("tan") and c != "tan_med"] + ["tan_med"]
    for c in cols:
        f = fit_line(df.M_nom, df[c], origin); gm = 1 / (f["slope"] * disp)
        f.update(GM=gm, GM_se=gm * f["se"] / abs(f["slope"]), KG=km - gm - fsc_corr); out[c] = f
    return out


def sensitivity(df, plan, ship, disp, origin=False):
    """Variação percentual do GM para +1 % em cada fonte de erro e para meia resolução em uma leitura."""
    M, t = df.M_nom.values, df.tan_med.values
    gm = lambda M_, t_, d_=disp: 1 / (fit_line(M_, t_, origin)["slope"] * d_)
    g0 = gm(M, t); res = np.mean([r for _, r in plan.pend]); L = np.mean([l for l, _ in plan.pend])
    out = {"massa +1 %": gm(M * 1.01, t), "distância +1 %": gm(M * 1.01, t),
           "comprimento do pêndulo +1 %": gm(M, t / 1.01), "deflexão lida +1 %": gm(M, t * 1.01),
           "deslocamento Δ +1 %": gm(M, t, disp * 1.01)}
    i_max = int(np.argmax(np.abs(M))); tt = t.copy(); tt[i_max] += res / 2000 / L
    out["½ resolução (leitura de maior momento)"] = gm(M, tt)
    nz = np.where(np.abs(M) > 0)[0]; i_min = nz[int(np.argmin(np.abs(M[nz])))]
    tt = t.copy(); tt[i_min] += res / 2000 / L; out["½ resolução (leitura de menor momento)"] = gm(M, tt)
    return pd.DataFrame({"fonte": list(out), "ΔGM (%)": [(v / g0 - 1) * 100 for v in out.values()]})


def mc_gm(ship, plan, err, n=200, seed=1, sys=(0.3, 0.3, 0.1, 0.3)):
    """Monte Carlo: sorteia erros SISTEMÁTICOS (massa, distância, comprimento, Δ; desvio-padrão em %) e
    aleatórios (ruído/vento/resolução já em err). Retorna GM estimado de cada prova."""
    rng = np.random.default_rng(seed); gms = []
    for i in range(n):
        e = replace(err, mass_pct=err.mass_pct + rng.normal(0, sys[0]), dist_pct=err.dist_pct + rng.normal(0, sys[1]),
                    len_pct=[x + rng.normal(0, sys[2]) for x in err.len_pct], disp_pct=err.disp_pct + rng.normal(0, sys[3]))
        df = simulate_test(ship, plan, e, seed=int(rng.integers(1e9)))
        gms.append(process(df, ship, ship.disp * (1 + e.disp_pct / 100))["tan_med"]["GM"])
    return np.array(gms)


# ------------------------------------------------------------------ planejamento
def predict(ship, plan):
    """Tabela de previsão por leitura: momento, φ metacêntrico, φ pela curva GZ, deflexão por pêndulo."""
    _, Mreal, peq = phi_series(ship, plan, Err()); Mnom = Mreal
    gm = ship.KM - ship.KG
    pm = np.degrees(np.arctan(Mnom / (ship.disp * gm)))
    t = pd.DataFrame({"leitura": range(len(Mnom)), "yA": [s[0] for s in plan.seq], "yB": [s[1] for s in plan.seq],
                      "M (t·m)": Mnom, "φ metacêntrico (°)": pm, "φ curva GZ (°)": peq})
    t["dif (%)"] = np.where(np.abs(pm) > 1e-9, (pm - peq) / np.where(pm == 0, 1, pm) * 100, 0)
    for k, (L, _) in enumerate(plan.pend): t[f"δ{k+1} (mm)"] = L * np.tan(np.radians(peq)) * 1000
    return t


def plan_precision(ship, plan):
    """Incerteza relativa PREVISTA do GM [%] só pela resolução dos pêndulos (erro de regressão).
    σ_tanφ = (res/√12)/L; σ_slope = σ_tan/√Sxx; combina pêndulos independentes."""
    M = plan.n_g * plan.m_w * np.array(plan.seq, float).sum(1); sxx = ((M - M.mean()) ** 2).sum()
    if sxx == 0: return np.inf
    inv = sum((L * 1000 / (r / np.sqrt(12))) ** 2 for L, r in plan.pend)       # 1/σ_tan² somado
    sig_t = 1 / np.sqrt(inv); slope = 1 / (ship.disp * (ship.KM - ship.KG))
    return float(sig_t / np.sqrt(sxx) / slope * 100)


def suggest_plan(ship, lim, phi_lo=1.5, phi_hi=3.0, tol_pct=1.0, pend=((12., 1.), (18., 1.))):
    """Busca em grade (n por grupo, d) com massa calculada p/ atingir φ alvo = (φ_lo+φ_hi)/2.
    Critérios: massa total, massa unitária, espaço (d), precisão (σ_GM ≤ tol_pct), faixa de φ.
    Complexidade = nº de pesos × movimentações (8)."""
    gm = ship.KM - ship.KG; ph = np.radians((phi_lo + phi_hi) / 2); rows = []
    for n in range(1, lim["n_max"] + 1):
        for d in np.linspace(0.4 * lim["y_max"], lim["y_max"], 7):
            mg = ship.disp * gm * np.tan(ph) / (2 * d)               # massa de cada grupo p/ φ_max alvo
            mw = mg / n; p = Plan(n, round(mw, 1), round(d, 1), list(pend))
            prec = plan_precision(ship, p); phimax = predict(ship, p)["φ curva GZ (°)"].abs().max()
            ok = dict(massa_total=2 * mg <= lim["m_total"], massa_unit=mw <= lim["w_unit"],
                      faixa=phi_lo - .3 <= phimax <= phi_hi + .3, precisao=prec <= tol_pct)
            rows.append(dict(n_g=n, m_w=round(mw, 1), d=round(d, 1), M_total=round(2 * mg, 1), phi_max=round(phimax, 2),
                             sigma_GM_pct=round(prec, 3), complexidade=2 * n * 8, viavel=all(ok.values()),
                             falha=", ".join(k for k, v in ok.items() if not v)))
    t = pd.DataFrame(rows)
    return t.sort_values(["viavel", "complexidade", "M_total"], ascending=[False, True, True]).reset_index(drop=True)


# ------------------------------------------------------------------ diagnóstico automático
def diagnose(df, plan, ship, res, lim, tol_res=0.01):
    """Alertas usando SÓ dados medidos/declarados (o simulador de erros é desconhecido para o 'aluno')."""
    A = []
    add = lambda sev, inc, hip, ver, acao, dec: A.append(dict(gravidade=sev, inconsistência=inc, hipótese=hip,
                                                          verificação=ver, ação=acao, decisão=dec))
    gm_t = ship.KM - ship.KG; phimax = df.phi_est.abs().max(); n = len(plan.pend)
    if phimax < lim["phi_min"]:
        add("ALTA", f"Inclinação máxima {phimax:.2f}° < faixa mínima ({lim['phi_min']}°)",
            "Pesos/distância insuficientes: erro relativo de leitura alto", "Reavaliar planejamento e resolução dos pêndulos",
            "Aumentar massa ou distância; usar pêndulo mais longo", "REPETIR")
    if phimax > lim["phi_max"]:
        add("ALTA", f"Inclinação máxima {phimax:.2f}° > faixa recomendada ({lim['phi_max']}°)",
            "Aproximação metacêntrica (tanφ ∝ M) deixa de valer; GZ não linear", "Comparar φ medido × previsto pela curva GZ",
            "Reduzir pesos/distância ou corrigir com a curva GZ", "REPETIR")
    if n >= 2:
        s1, s2 = res["tan1"]["slope"], res["tan2"]["slope"]
        se = np.hypot(res["tan1"]["se"] / s1, res["tan2"]["se"] / s2)            # incerteza relativa da razão
        if abs(s1 / s2 - 1) > max(0.01, 3 * se):
            add("ALTA", f"Pêndulos 1 e 2 discordam: razão das inclinações = {s1/s2:.3f}",
                "Comprimento declarado ≠ real (razão constante) ou escala/calibração do instrumento", "Remedir os fios (suspensão até o centro da bob) e a régua",
                "Corrigir comprimentos e reprocessar; se persistir, usar só o pêndulo validado", "REPETIR" if abs(s1/s2-1) < .05 else "SUSPENDER")
        d = (df.tan1 - df.tan2).values; mad = 1.4826 * np.median(np.abs(d - np.median(d))) + 1e-12
        tol_d = 3 * np.hypot(plan.pend[0][1] / plan.pend[0][0], plan.pend[1][1] / plan.pend[1][0]) / 1000
        for i in np.where((np.abs(d - np.median(d)) > 3.5 * mad) & (np.abs(d - np.median(d)) > tol_d))[0]:
            k = 1 if abs(res["tan1"]["resid"][i]) > abs(res["tan2"]["resid"][i]) else 2
            add("ALTA", f"Leitura {int(df.leitura[i])}: pêndulos divergem ({d[i]*1000:.2f} mrad); resíduo maior no pêndulo {k}",
                "Erro grosseiro de leitura/anotação, pêndulo tocado, ou deslocamento da referência", "Comparar com as leituras vizinhas e com o outro pêndulo",
                "Repetir a leitura após novo equilíbrio", "REPETIR LEITURA")
    z = df[df.M_nom == 0]; sp = (z.tan_med.max() - z.tan_med.min()) if len(z) > 1 else 0
    tol_z = 3 * np.mean([r / L for L, r in plan.pend]) / 1000 * 2 + 2 * np.radians(tol_res)
    if sp > tol_z:
        add("ALTA", f"Leituras na posição zero não retornam à origem (dispersão {sp*1000:.2f} mrad)",
            "Vento/corrente, amarras tensionadas, histerese, líquido em tanques, referência do pêndulo deslocada",
            "Verificar amarras, sondagem de tanques, fixação dos pêndulos, condições ambientais", "Soltar amarras; esperar condição estável; repetir zero",
            "REPETIR" if sp < 3 * tol_z else "SUSPENDER")
    r = res["tan_med"]["resid"]; h = len(r) // 2
    if len(r) >= 6 and abs(r[:h].mean() - r[h:].mean()) > 3 * res["tan_med"]["rms"] / np.sqrt(h) and res["tan_med"]["rms"] > 0:
        add("MÉDIA", "Resíduos com tendência temporal (1ª × 2ª metade da prova)", "Deriva de referência, vento variável ou variação de calado/densidade",
            "Plotar resíduos na ordem das leituras; checar ocorrências no diário", "Repetir bordo afetado", "REPETIR")
    pos, neg = df[df.M_nom > 0], df[df.M_nom < 0]
    if len(pos) >= 2 and len(neg) >= 2:
        sp_ = fit_line(pos.M_nom, pos.tan_med - z.tan_med.mean())["slope"]; sn_ = fit_line(neg.M_nom, neg.tan_med - z.tan_med.mean())["slope"]
        if abs(sp_ / sn_ - 1) > 0.05:
            add("MÉDIA", f"Assimetria BE × BB: razão de inclinações {sp_/sn_:.3f}", "Amarras/vento unilateral, trim ou distâncias medidas diferentes por bordo",
                "Remedir distâncias por bordo; verificar amarras", "Repetir bordo discrepante", "REPETIR")
    if phimax > 0:
        big = df[df.phi_est.abs() > 0.5 * phimax]; low = df[(df.phi_est.abs() <= 0.5 * phimax) & (df.M_nom != 0)]
        if len(big) >= 2 and len(low) >= 2:
            g_b = 1 / (fit_line(big.M_nom, big.tan_med)["slope"] * ship.disp); g_l = 1 / (fit_line(low.M_nom, low.tan_med)["slope"] * ship.disp)
            if abs(g_b / g_l - 1) > 0.03:
                add("MÉDIA", f"GM depende do ângulo ({g_l:.2f} m a baixo × {g_b:.2f} m a alto φ)", "Efeito não-linear (GZ não metacêntrico) ou superfície livre/amarras",
                    "Comparar com previsão pela curva GZ", "Restringir ajuste à faixa linear", "ACEITAR COM RESSALVA")
    kg = res["tan_med"]["KG"]
    if abs(kg - ship.KG) > 0.02 * ship.KG:
        add("ALTA", f"KG medido {kg:.2f} m difere {abs(kg-ship.KG)/ship.KG*100:.1f} % do KG de referência ({ship.KG:.2f} m)",
            "Superfície livre não corrigida, massa/distância incorretas (sistemático), Δ/KM errados (calado/densidade), amarras",
            "Sondar todos os tanques; pesar pesos; medir distâncias por 2 métodos; reconferir calado, densidade e leitura de marcas",
            "Corrigir FSC, recalibrar massas, repetir ensaio", "REPETIR / SUSPENDER")
    if not A:
        add("INFO", "Nenhuma inconsistência detectada pelos testes estatísticos", "Erros sistemáticos (massa, distância, Δ, FSC) NÃO são visíveis no ajuste linear",
            "Checklist obrigatório: pesar pesos, medir distâncias, sondar tanques, calado/densidade", "Executar checklist", "ACEITAR após checklist")
    return pd.DataFrame(A)

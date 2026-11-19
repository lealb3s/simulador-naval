"""
incl_app.py - AP2: simulador de prova de inclinação (GM e KG).   Executar:  streamlit run ap2_inclinacao_app.py
"""
import io, json
import numpy as np, pandas as pd, streamlit as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from dataclasses import replace
import incl_core as ic
try:
    import hydro_core as hc          # hidrostática da AP1.2 (opcional)
except Exception:
    hc = None

st.set_page_config(page_title="AP2 – Prova de inclinação", layout="wide")
st.title("⚖️ AP2 – Simulador de prova de inclinação")
T1, T2, T3, T4, T5, T6, T7 = st.tabs(["I Dados", "II Pesos", "III Pêndulos", "IV Prova virtual",
                                      "V Erros e diagnóstico", "VI Processamento", "VII Configurações / relatório"])
S = st.session_state
S.setdefault("log", []); S.setdefault("cfg_res", None)
showfig = lambda f: (st.pyplot(f), plt.close(f))


@st.cache_data
def hydro_at(T, keel=0.017, rho=1.025):
    """KM, BM, KB e deslocamento da hidrostática da AP1.2 para o calado extremo T."""
    h = hc.hydrostatics_moulded(max(T - keel, 0.0))
    return dict(disp=rho * (h["V"] + h["WSA"] * keel), KM=h["KMt"], BM=h["BMt"], KB=h["VCB"])


# ======================================================================= PARTE I
with T1:
    st.subheader("Propriedades da embarcação e limites do ensaio")
    c1, c2 = st.columns(2)
    src = c1.radio("Origem das propriedades", ["Hidrostática da AP1.2 (hydro_core.py)", "Manual / arquivo JSON"], horizontal=True) if hc else "Manual"
    up = c2.file_uploader("Arquivo JSON de entrada (opcional)", type="json")
    base = dict(disp=123800.0, draft=8.0, KM=39.5, KG=16.0, BM=34.4, B=60.0, D=30.0)
    if up:
        base.update(json.load(up))
    draft = c1.number_input("Calado da condição de ensaio [m]", 1.0, 30.0, float(base["draft"]), 0.5)
    if src.startswith("Hidro"):
        h = hydro_at(draft); base.update(disp=h["disp"], KM=h["KM"], BM=h["BM"])
    k = f"{draft}{src[:3]}{up.name if up else ''}"                  # chave: atualiza os campos quando a origem muda
    a, b, c, d_ = st.columns(4)
    disp = a.number_input("Deslocamento Δ [t]", 1000.0, 1e7, float(base["disp"]), 100.0, key="disp" + k)
    KM = b.number_input("KM transversal [m]", 1.0, 100.0, float(base["KM"]), 0.01, key="km" + k)
    KG = c.number_input("KG de referência [m]", 0.5, 100.0, float(base["KG"]), 0.01, key="kg" + k)
    BM = d_.number_input("BMt [m] (gera a curva GZ)", 0.1, 100.0, float(base["BM"]), 0.01, key="bm" + k)
    a, b = st.columns(2)
    Bw = a.number_input("Boca B [m]", 1.0, 100.0, float(base["B"])); Dp = b.number_input("Pontal D [m]", 1.0, 100.0, float(base["D"]))
    with st.expander("Dinâmica de balanço (para o transitório)"):
        k_roll = st.slider("Raio de giração / B", 0.25, 0.45, 0.35); zeta = st.slider("Razão de amortecimento ζ", 0.01, 0.2, 0.05)
    gzf = st.file_uploader("Curva GZ da AP1.3 (CSV: ângulo [°], GZ [m])", type=["csv", "txt"])
    ship = ic.Ship(disp, draft, KM, KG, BM, Bw, Dp, k_roll, zeta)
    if gzf:
        g0 = pd.read_csv(io.BytesIO(gzf.getvalue())); g = g0.iloc[:, :2].dropna().sort_values(g0.columns[0])
        ship = replace(ship, gz_deg=tuple(g.iloc[:, 0]), gz_m=tuple(g.iloc[:, 1]))
    else:
        st.caption("⚠️ Curva GZ gerada por fórmula de parede lateral — importe a curva da AP1.3 para usar a sua.")
    gm_ref, gm_c = KM - KG, ic.gm_curve(ship)
    st.metric("GM de referência (KM − KG)", f"{gm_ref:.3f} m")
    if abs(gm_c / gm_ref - 1) > 0.03:
        st.error(f"Curva GZ inconsistente: GM implícito {gm_c:.2f} m ≠ KM−KG {gm_ref:.2f} m (>3 %).")
    if hc and src.startswith("Hidro"): st.success("Δ, KM e BM calculados com a AP1.2 – compatíveis com a hidrostática.")
    elif hc:
        hh = hydro_at(draft); dd = abs(disp / hh["disp"] - 1) * 100
        (st.warning if dd > 1 else st.success)(f"Δ informado difere {dd:.2f} % do Δ hidrostático no calado {draft} m.")
    st.download_button("⬇️ Modelo JSON de entrada", json.dumps(dict(disp=disp, draft=draft, KM=KM, KG=KG, BM=BM, B=Bw, D=Dp)), "entrada_AP1.json")
    fig, ax = plt.subplots(figsize=(6, 2.8)); ax.plot(ship.gz_deg, ship.gz_m); ax.plot([0, 10], [0, np.radians(10) * gm_c], "--", c="gray", label="tangente (GM)")
    ax.set_xlabel("φ [°]"); ax.set_ylabel("GZ [m]"); ax.legend(); ax.grid(alpha=.3); showfig(fig)
    st.markdown("**Limitações físicas**")
    a, b, c, d_, e_, f_ = st.columns(6)
    lim = dict(y_max=a.number_input("y máx. dos pesos [m]", 1.0, 50.0, min(27.0, Bw / 2 - 3), 0.5),
               L_max=b.number_input("L máx. pêndulo [m]", 1.0, 60.0, 25.0), m_total=c.number_input("Massa total máx. [t]", 10.0, 1e5, 8000.0, 100.0),
               w_unit=d_.number_input("Massa unit. máx. [t]", 1.0, 5000.0, 400.0, 10.0), n_max=int(e_.number_input("Nº máx. pesos/grupo", 1, 30, 6)),
               phi_min=f_.number_input("φ mín. recomendado [°]", 0.1, 5.0, 1.0, 0.1))
    lim["phi_max"] = st.number_input("φ máx. recomendado [°] (limite da aproximação metacêntrica)", 1.0, 15.0, 4.0, 0.5)
    lim["tol"] = st.number_input("Tolerância de oscilação residual para ler [°]", 0.001, 0.2, 0.01, 0.001, format="%.3f")

# ======================================================================= PARTE III (pêndulos; definidos antes do plano)
with T3:
    st.subheader("Instrumentos: pêndulos virtuais")
    a, b, c, d_ = st.columns(4)
    L1 = a.number_input("L pêndulo 1 [m]", 0.5, lim["L_max"], min(12.0, lim["L_max"]), 0.5); L2 = b.number_input("L pêndulo 2 [m]", 0.5, lim["L_max"], min(18.0, lim["L_max"]), 0.5)
    use3 = c.checkbox("Usar 3º pêndulo"); L3 = c.number_input("L pêndulo 3 [m]", 0.5, lim["L_max"], min(6.0, lim["L_max"]), 0.5)
    res_mm = d_.number_input("Resolução da leitura [mm]", 0.1, 20.0, 1.0, 0.1)
    pend = [(L1, res_mm), (L2, res_mm)] + ([(L3, res_mm)] if use3 else [])

# ======================================================================= PARTE II
with T2:
    st.subheader("Planejamento dos pesos inclinantes")
    gmr = ship.KM - ship.KG; dm = min(25.0, lim["y_max"])
    a, b, c = st.columns(3)
    n_g = a.slider("Pesos por grupo (grupos A e B)", 1, 30, min(4, lim["n_max"]))
    m_w = b.number_input("Massa de cada peso [t]", 0.1, 20000.0, min(350.0, lim["w_unit"]), 10.0)
    d = c.slider("Distância de movimentação d [m]", 0.5, float(lim["y_max"] * 1.5), float(dm), 0.5)
    phi_t = a.number_input("φ alvo [°] (calculadora)", 0.1, 15.0, 2.0, 0.1)
    need = ship.disp * gmr * np.tan(np.radians(phi_t)) / (2 * n_g * d)
    b.metric("Massa por peso p/ φ alvo (dois grupos movidos)", f"{need:.1f} t")
    with st.expander("Sequência de movimentações (editável: yA, yB em m, + = boreste)"):
        ed = st.data_editor(pd.DataFrame(ic.default_seq(d), columns=["yA", "yB"]), num_rows="dynamic", key=f"seq{d}")
    seq = [tuple(r) for r in ed.dropna().values.tolist()]
    plan = ic.Plan(n_g, m_w, d, pend, seq)
    Mtot = 2 * n_g * m_w; pred = ic.predict(ship, plan); pm = pred["φ curva GZ (°)"].abs().max()
    chk = [(len(seq) >= 8, f"{len(seq)} leituras (mínimo 8)"), (Mtot <= lim["m_total"], f"Massa total {Mtot:.0f} t ≤ {lim['m_total']:.0f} t"),
           (m_w <= lim["w_unit"], f"Massa unitária {m_w:.0f} t ≤ {lim['w_unit']:.0f} t"), (max(max(abs(p) for p in s) for s in seq) <= lim["y_max"], f"Posições ≤ {lim['y_max']} m"),
           (lim["phi_min"] <= pm <= lim["phi_max"], f"φ máx. previsto {pm:.2f}° na faixa [{lim['phi_min']}, {lim['phi_max']}]°"),
           (any(s[0] < 0 for s in seq) and any(s[0] > 0 for s in seq), "Inclinações para ambos os bordos")]
    for ok, msg in chk: (st.success if ok else st.error)(("✔ " if ok else "✘ ") + msg)
    st.dataframe(pred.style.format(precision=3), use_container_width=True)
    st.caption(f"Incerteza prevista do GM só pela resolução: **{ic.plan_precision(ship, plan):.3f} %**")
    st.markdown("#### Investigação obrigatória: três configurações")
    scale = lambda ph: replace(plan, m_w=ship.disp * gmr * np.tan(np.radians(ph)) / (2 * n_g * d))
    sug = ic.suggest_plan(ship, lim, pend=tuple(pend)); best = sug.iloc[0]
    cfgs = {"A – baixa inclinação (0,3°)": scale(0.3), "B – excessiva (10°)": scale(10.0),
            "C – sugerida (critérios)": ic.Plan(int(best.n_g), float(best.m_w), float(best.d), pend)}
    rows = []
    for nm, p in cfgs.items():
        dfq = ic.simulate_test(ship, p, ic.Err()); rq = ic.process(dfq, ship)["tan_med"]
        mc = ic.mc_gm(ship, p, ic.Err(noise_mm=0.3, wind_sigma=0.005), n=60, sys=(0, 0, 0, 0))
        rows.append({"Configuração": nm, "n/grupo": p.n_g, "m/peso (t)": round(p.m_w, 1), "d (m)": p.d, "M total (t)": round(2 * p.n_g * p.m_w),
                     "φ máx (°)": round(ic.predict(ship, p)["φ curva GZ (°)"].abs().max(), 2), "σ_GM prev. (%)": round(ic.plan_precision(ship, p), 3),
                     "σ_GM Monte Carlo (%)": round(mc.std() / mc.mean() * 100, 3), "viés metacêntrico (%)": round((rq["GM"] / gmr - 1) * 100, 3)})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    phs = np.linspace(0.1, 12, 30); sg, bs = [], []
    for ph in phs:
        p = scale(ph); sg.append(ic.plan_precision(ship, p)); bs.append((ic.process(ic.simulate_test(ship, p, ic.Err()), ship)["tan_med"]["GM"] / gmr - 1) * 100)
    fig, ax = plt.subplots(figsize=(8, 3.2)); ax.semilogy(phs, sg, label="σ_GM por resolução (%)"); ax.semilogy(phs, np.abs(bs) + 1e-4, label="|viés metacêntrico| (%)")
    ax.axvspan(lim["phi_min"], lim["phi_max"], alpha=.15, color="g", label="faixa recomendada"); ax.set_xlabel("φ máx. [°]"); ax.legend(); ax.grid(alpha=.3); showfig(fig)
    st.markdown("**Critérios usados na sugestão (grade n × d):** massa total ≤ limite; massa unitária ≤ capacidade de içamento; φ previsto na faixa alvo; σ_GM ≤ 1 %; "
                "menor complexidade (nº de pesos × movimentações). Sem esses critérios nenhuma massa é 'ideal'.")
    st.dataframe(sug.head(8), use_container_width=True)
    if best.viavel: st.success(f"Plano justificado: {int(best.n_g)} pesos/grupo × {best.m_w} t, d = {best.d} m → φ máx {best.phi_max}°, σ_GM {best.sigma_GM_pct} %, complexidade {best.complexidade}.")
    else: st.warning(f"Nenhuma combinação satisfaz todos os critérios; a melhor viola: {best.falha}. Relaxe os limites ou use mais pesos/ lastro líquido.")

# ======================================================================= PARTE V (widgets de erro)
with T5:
    st.subheader("Simulação de erros")
    on = st.checkbox("Ativar erros", value=False); er = ic.Err()
    if on:
        a, b, c = st.columns(3)
        er.mass_pct = a.slider("Erro de massa dos pesos [%]", -10.0, 10.0, 0.0, 0.1); er.dist_pct = b.slider("Erro na distância movimentada [%]", -10.0, 10.0, 0.0, 0.1)
        er.noise_mm = c.slider("Ruído de leitura σ [mm]", 0.0, 5.0, 0.0, 0.1)
        er.len_pct = [a.slider(f"Comprimento real do pêndulo {i+1} vs declarado [%]", -10.0, 10.0, 0.0, 0.1) for i in range(3)]
        er.wind_sigma = b.slider("Vento variável σ [°]", 0.0, 0.3, 0.0, 0.005); er.wind_bias = b.slider("Vento constante (viés) [°]", -0.5, 0.5, 0.0, 0.01)
        er.k_moor = c.slider("Amarras tensionadas [t·m por °]", 0.0, 5000.0, 0.0, 50.0)
        st.markdown("**Superfície livre**"); a, b, c, d_ = st.columns(4)
        er.tank_l = a.number_input("Comprimento do tanque [m]", 0.0, 100.0, 0.0); er.tank_b = b.number_input("Largura do tanque [m]", 0.0, 60.0, 0.0)
        er.tank_fill = c.slider("Enchimento (parcial se 0<x<1)", 0.0, 1.0, 0.0, 0.05); er.fsc_declared = d_.checkbox("FSC corrigida no cálculo do KG")
        st.markdown("**Referência / leitura / calado**"); a, b, c = st.columns(3)
        er.ref_shift_mm = [a.number_input("Deslocamento de referência do pêndulo 1 [mm]", -50.0, 50.0, 0.0)] + [0.0, 0.0]; er.ref_shift_from = int(b.number_input("… a partir da leitura", 0, 20, 5))
        er.gross_mm = c.number_input("Erro grosseiro [mm]", -100.0, 100.0, 0.0); er.gross_idx = int(a.number_input("… na leitura", 0, 20, 3)); er.gross_pend = int(b.number_input("… no pêndulo (0=1º)", 0, 2, 0))
        er.disp_pct = c.slider("Erro de Δ (calado/densidade) [%]", -3.0, 3.0, 0.0, 0.1); er.km_err = a.slider("Erro adotado no KM [m]", -1.0, 1.0, 0.0, 0.01)
    errs = [f"massa {er.mass_pct:+.1f}%" if er.mass_pct else "", f"dist {er.dist_pct:+.1f}%" if er.dist_pct else "", "FSC" if ic.fsc_of(er, ship) else "",
            f"vento σ{er.wind_sigma}°" if er.wind_sigma or er.wind_bias else "", "amarras" if er.k_moor else "", f"L {er.len_pct}" if any(er.len_pct) else "",
            "ref.desl." if er.ref_shift_mm[0] else "", "grosseiro" if er.gross_mm else "", "Δ/KM" if er.disp_pct or er.km_err else ""]
    cond = "; ".join(e for e in errs if e) or "ideal"
    st.caption(f"Condição ativa: {cond}  ·  FSC real = {ic.fsc_of(er, ship):.3f} m")

# ======================================================================= PARTE IV (interativa)
def _reset():
    S.log, S.phi_prev, S.tw = [], 0.0, 0.0; S.wsig = None


def _auto(dfa):
    S.log = dfa.to_dict("records"); S.phi_prev = float(dfa.phi_eq.iloc[-1]); S.tw = 0.0


def _register(row):
    S.log.append(row); S.phi_prev = row["phi_eq"]; S.tw = 0.0


with T4:
    st.subheader("Execução virtual — você decide quais pesos colocar e onde")
    S.setdefault("phi_prev", 0.0); S.setdefault("tw", 0.0); S.setdefault("wkey", 0)
    seed = st.number_input("Semente aleatória", 0, 9999, 1)
    sig = (plan.n_g, plan.m_w)
    if S.get("wsig") != sig or S.get("weights") is None:             # (re)cria a tabela de pesos quando o plano muda
        S.weights = pd.DataFrame({"peso": [f"A{i+1}" for i in range(plan.n_g)] + [f"B{i+1}" for i in range(plan.n_g)],
                                  "a_bordo": True, "y_m": 0.0, "massa_t": float(plan.m_w)})
        S.wsig = sig; S.wkey += 1
    st.markdown("**Tabela de pesos** — marque/desmarque *a bordo* e edite a posição transversal y (+ BE / − BB).")
    ed = st.data_editor(S.weights, key=f"w{S.wkey}", hide_index=True, use_container_width=True,
                        column_config={"peso": st.column_config.TextColumn("peso", disabled=True), "a_bordo": st.column_config.CheckboxColumn("a bordo?"),
                                       "y_m": st.column_config.NumberColumn("y [m]", min_value=-60.0, max_value=60.0, step=0.5),
                                       "massa_t": st.column_config.NumberColumn("massa [t]", min_value=0.0, step=10.0)})

    def setw(*pairs):                                                 # pairs = (prefixo do grupo, y); aplica tudo numa só cópia
        W = ed.copy()
        for prefix, y in pairs:
            m = W.peso.str.startswith(prefix); W.loc[m, "y_m"] = float(y); W.loc[m, "a_bordo"] = True
        S.weights = W; S.wkey += 1

    q = st.columns(6)
    if q[0].button("A → BE (+d)"): setw(("A", plan.d)); st.rerun()
    if q[1].button("A → BB (−d)"): setw(("A", -plan.d)); st.rerun()
    if q[2].button("B → BE (+d)"): setw(("B", plan.d)); st.rerun()
    if q[3].button("B → BB (−d)"): setw(("B", -plan.d)); st.rerun()
    if q[4].button("Todos ao centro"): setw(("A", 0.0), ("B", 0.0)); st.rerun()
    if q[5].button("Carregar passo sugerido"):
        k_ = min(len(S.log), len(plan.seq) - 1); setw(("A", plan.seq[k_][0]), ("B", plan.seq[k_][1])); st.rerun()
    st.caption("Pesos fora de bordo não geram momento. O estado de referência (Δ, KG, KM) já inclui os pesos na linha de centro.")

    on = ed[ed.a_bordo.astype(bool)]
    Mn = float((on.massa_t * on.y_m).sum())                                                   # momento declarado
    Mr = float((on.massa_t * (1 + er.mass_pct / 100) * on.y_m * (1 + er.dist_pct / 100)).sum())  # momento real (com erros)
    viol = ([f"{r.peso}: |y| = {abs(r.y_m):.1f} m > {lim['y_max']} m" for r in on.itertuples() if abs(r.y_m) > lim["y_max"]]
            + ([f"massa a bordo {on.massa_t.sum():.0f} t > {lim['m_total']:.0f} t"] if on.massa_t.sum() > lim["m_total"] else [])
            + [f"{r.peso}: {r.massa_t:.0f} t > capacidade unitária {lim['w_unit']:.0f} t" for r in on.itertuples() if r.massa_t > lim["w_unit"]])
    for v in viol: st.error("Limite físico violado — " + v)

    phi_new = float(np.degrees(ic.equilibrium(ship, Mr, ic.fsc_of(er, ship), er.k_moor))[0]); phi_prev = S.phi_prev; dphi = phi_new - phi_prev
    wn = ic.omega_n(ship, er); wd = wn * np.sqrt(1 - ship.zeta ** 2); tmin = ic.min_wait(ship, er, dphi, lim["tol"])
    tw_max = max(600.0, tmin * 1.5); S.tw = float(min(S.tw, tw_max))     # evita valor acima do máximo do slider
    tw = st.slider("Tempo de espera desde a última movimentação [s]", 0.0, tw_max, key="tw", step=5.0)
    env = abs(dphi) * np.exp(-ship.zeta * wn * tw) / np.sqrt(1 - ship.zeta ** 2); ok = env <= lim["tol"]
    phi_show = phi_new - dphi * np.exp(-ship.zeta * wn * tw) * np.cos(wd * tw)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("φ instantâneo", f"{phi_show:+.3f}°"); m2.metric("Momento nominal", f"{Mn:,.0f} t·m")
    m3.metric("Oscilação residual", f"{env:.4f}°", delta="liberado" if ok else "aguarde", delta_color="normal" if ok else "inverse")
    m4.metric("Espera mínima", f"{tmin:.0f} s")
    tt = np.linspace(0, max(600.0, tw * 1.2, tmin * 1.2), 400)
    fg, ax = plt.subplots(figsize=(8, 2.4)); ax.plot(tt, phi_new - dphi * np.exp(-ship.zeta * wn * tt) * np.cos(wd * tt)); ax.axvline(tw, c="r", ls="--"); ax.axhline(phi_new, c="gray", lw=.5)
    ax.set_xlabel("t [s]"); ax.set_ylabel("φ [°]"); ax.set_title(f"Transitório (período natural ≈ {2*np.pi/wn:.1f} s)"); ax.grid(alpha=.3); showfig(fg)

    force = (not ok) and st.checkbox("Forçar leitura mesmo com oscilação (para demonstrar o erro)")
    if not ok: st.error("Leitura bloqueada: aguarde o amortecimento do balanço (aumente o tempo de espera).")
    cfg_txt = ", ".join(f"{r.peso}:{r.y_m:+.1f}" for r in on.itertuples() if abs(r.y_m) > 1e-9) or "todos ao centro"
    j = len(S.log); rng = np.random.default_rng(int(seed) * 100 + j)
    row, _, _ = ic.reading_from_M(ship, plan.pend, er, j, Mn, Mr, phi_prev, tw, rng, lim["tol"])
    row.update(config=cfg_txt, n_a_bordo=len(on), condicoes=cond + ("; leitura forçada" if force else ""))
    c1_, c2_ = st.columns(2)
    c1_.button("📝 Registrar leitura", disabled=not (ok or force) or bool(viol), on_click=_register, args=(row,))
    c2_.button("⏩ Executar sequência completa (automático)", on_click=lambda: _auto(ic.simulate_test(ship, plan, er, seed=int(seed), tol=lim["tol"]).assign(condicoes=cond)))
    st.button("🔁 Reiniciar prova", on_click=_reset)

    # ---- progresso da prova (requisitos da AP2)
    Lg = pd.DataFrame(S.log)
    n_l = len(Lg); both = bool(n_l and (Lg.M_nom > 0).any() and (Lg.M_nom < 0).any()); n_zero = int((Lg.M_nom == 0).sum()) if n_l else 0
    st.markdown(f"{'✔' if n_l >= 8 else '✘'} {n_l}/8 leituras · {'✔' if both else '✘'} ambos os bordos · {'✔' if n_zero >= 2 else '✘'} {n_zero} verificações da posição inicial (≥2)")

    # ---- desenho da seção transversal (vista de ré: BB à esquerda, BE à direita)
    fig, ax = plt.subplots(figsize=(9, 5.4)); T, Bh, Dd, r = ship.draft, ship.B, ship.D, 3.0; ph = np.radians(phi_show)
    rot = lambda y, z: (y * np.cos(ph) + (z - T) * np.sin(ph), T + (-y * np.sin(ph) + (z - T) * np.cos(ph)))
    th = np.linspace(0, np.pi / 2, 12); Rr = [(Bh / 2 - r + r * np.sin(t), r - r * np.cos(t)) for t in th]
    hull = [(-Bh / 2, Dd), (-Bh / 2, r)] + [(-y, z) for y, z in Rr][::-1][1:] + Rr[1:] + [(Bh / 2, Dd)]
    ax.axhspan(-15, T, color="#cfe8ff", alpha=.6); ax.axhline(T, c="b", lw=1.2, label="linha de flutuação")
    ax.add_patch(Polygon([rot(*p) for p in hull], closed=False, fill=False, ec="k", lw=1.5)); ax.plot(*zip(rot(-Bh / 2, Dd), rot(Bh / 2, Dd)), "k", lw=2)
    stack, top = {}, 0
    for r_ in on.itertuples():                                       # cada peso a bordo; pesos próximos são empilhados
        kk = round(r_.y_m / 2.0); s_ = stack.get(kk, 0); stack[kk] = s_ + 1; top = max(top, s_ + 1); z0 = Dd + 3.0 * s_
        ax.add_patch(Polygon([rot(r_.y_m + dy, z0 + dz) for dy, dz in [(-1.8, 0), (1.8, 0), (1.8, 2.8), (-1.8, 2.8)]], color="tab:orange" if r_.peso.startswith("A") else "tab:purple", ec="k", lw=.4))
    n_off = len(ed) - len(on)
    ax.text(Bh * .73, Dd + 4, f"fora de bordo: {n_off} peso(s)\na bordo: {len(on)} · M = {Mn:,.0f} t·m", ha="right", fontsize=8, bbox=dict(boxstyle="round", fc="#eee"))
    for k, (Lk, _) in enumerate(plan.pend):
        ys = [-12, 12, 0][k]; sy, sz = rot(ys, Dd); dlt = Lk * np.tan(ph) * 1000
        ax.plot([sy, sy], [sz, sz - Lk], "r", lw=1); ax.plot(*zip((sy, sz), rot(ys, Dd - Lk)), "k--", lw=.7); ax.text(sy, sz - Lk - 1.5, f"P{k+1}: δ={dlt:.0f} mm", ha="center", fontsize=7, color="r")
    Gx, Gz = rot(0, ship.KG); Bx, Bz = rot(ship.BM * np.tan(ph), (ship.KM - ship.BM) + .5 * ship.BM * np.tan(ph) ** 2); Mx, Mz = rot(0, ship.KM)
    for (x_, z_), nm, c_ in [((Gx, Gz), "G", "g"), ((Bx, Bz), "B'", "b"), ((Mx, Mz), "M", "m")]: ax.plot(x_, z_, "o", c=c_); ax.text(x_ + .8, z_, nm, color=c_)
    ax.text(-Bh / 2, Dd + 6 + 3 * top, "◀ BOMBORDO (BB)", fontsize=9); ax.text(Bh / 2, Dd + 6 + 3 * top, "BOreste (BE) ▶", fontsize=9, ha="right")
    ax.set_xlim(-Bh * .75, Bh * .75); ax.set_ylim(-3, Dd + 10 + 3 * top); ax.set_aspect("equal"); ax.set_title(f"φ = {phi_show:+.3f}°  (vista de ré) · laranja = grupo A, roxo = grupo B"); ax.legend(loc="lower right"); showfig(fig)
    if n_l >= 2:
        fg, ax = plt.subplots(figsize=(6, 2.6)); ax.plot(Lg.M_nom, Lg.tan_med, "o"); ax.set_xlabel("M [t·m]"); ax.set_ylabel("tanφ"); ax.set_title("Leituras registradas"); ax.grid(alpha=.3); showfig(fg)
    st.markdown("**Histórico da prova**")
    if S.log:
        H = pd.DataFrame(S.log); st.dataframe(H.style.format(precision=4), use_container_width=True)
        bio = io.BytesIO(); H.to_excel(bio, index=False, engine="openpyxl")
        c1_, c2_ = st.columns(2); c1_.download_button("⬇️ CSV", H.to_csv(index=False), "prova_inclinacao.csv"); c2_.download_button("⬇️ Excel", bio.getvalue(), "prova_inclinacao.xlsx")

# ======================================================================= processamento (cálculo)
dfl = pd.DataFrame(S.log) if len(S.log) >= 4 else None; res = None
with T6:
    st.subheader("Processamento experimental: GM e KG")
    if dfl is None: st.info("Registre ao menos 4 leituras (ou use 'Executar sequência completa') na aba IV.")
    else:
        origin = st.checkbox("Forçar ajuste pela origem", False); fsc_corr = ic.fsc_of(er, ship) if er.fsc_declared else 0.0
        dadopt, kmadopt = ship.disp * (1 + er.disp_pct / 100), ship.KM + er.km_err
        res = ic.process(dfl, ship, dadopt, kmadopt, fsc_corr, origin)
        gm_phys = ic.gm_curve(ship) - ic.fsc_of(er, ship); kg_phys = ship.KM - gm_phys
        tb = pd.DataFrame([{"Instrumento": c, "GM (m)": v["GM"], "± σ (m)": v["GM_se"], "KG (m)": v["KG"], "R²": v["r2"], "RMS res. (mrad)": v["rms"] * 1000,
                            "ΔGM vs ref (%)": (v["GM"] / gm_ref - 1) * 100, "ΔKG vs ref (m)": v["KG"] - ship.KG} for c, v in res.items()])
        st.dataframe(tb.style.format(precision=4), use_container_width=True)
        st.write(f"**Referência:** GM = {gm_ref:.3f} m, KG = {ship.KG:.3f} m · GM físico sob erros (FSC) = {gm_phys:.3f} m")
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 3.8)); xs = np.linspace(dfl.M_nom.min(), dfl.M_nom.max(), 50)
        for c, v in res.items():
            a1.plot(dfl.M_nom, dfl[c], "o", label=c, ms=4); a1.plot(xs, v["icpt"] + v["slope"] * xs, lw=.8)
            a2.plot(dfl.leitura, v["resid"] * 1000, "o-", label=c, ms=4)
        a1.set_xlabel("M [t·m]"); a1.set_ylabel("tan φ"); a1.legend(); a1.grid(alpha=.3); a2.axhline(0, c="k", lw=.5); a2.set_xlabel("nº da leitura"); a2.set_ylabel("resíduo [mrad]"); a2.grid(alpha=.3)
        a1.set_title("tanφ × momento"); a2.set_title("Resíduos do ajuste"); showfig(fig)
        st.markdown("**Sensibilidade (±1 % por fonte; ½ resolução em uma leitura)**"); sn = ic.sensitivity(dfl, plan, ship, dadopt, origin); a, b = st.columns(2)
        a.dataframe(sn.style.format(precision=3)); fg, ax = plt.subplots(figsize=(5, 3)); ax.barh(sn["fonte"], sn["ΔGM (%)"]); ax.grid(alpha=.3); b.pyplot(fg); plt.close(fg)
        st.markdown("**Incerteza: aleatória × sistemática (Monte Carlo)**"); a, b, c, d_, e_ = st.columns(5)
        sy = (a.number_input("σ massa [%]", 0.0, 5.0, 0.3), b.number_input("σ distância [%]", 0.0, 5.0, 0.3), c.number_input("σ comprimento [%]", 0.0, 5.0, 0.1), d_.number_input("σ Δ [%]", 0.0, 5.0, 0.3))
        nmc = int(e_.number_input("Nº de provas", 20, 500, 150))
        if st.button("Rodar Monte Carlo"):
            base_e = replace(er, noise_mm=max(er.noise_mm, 0.3), wind_sigma=max(er.wind_sigma, 0.005))
            g_all = ic.mc_gm(ship, plan, base_e, nmc, 7, sy); g_rnd = ic.mc_gm(ship, plan, base_e, nmc, 8, (0, 0, 0, 0))
            fg, ax = plt.subplots(figsize=(8, 3)); ax.hist(g_all, 25, alpha=.6, label="aleatório + sistemático"); ax.hist(g_rnd, 25, alpha=.6, label="só aleatório"); ax.axvline(gm_ref, c="k", ls="--", label="GM ref")
            ax.legend(); ax.set_xlabel("GM [m]"); showfig(fg)
            st.write(f"σ aleatório = {g_rnd.std()/g_rnd.mean()*100:.3f} % · σ total = {g_all.std()/g_all.mean()*100:.3f} % · σ sistemático teórico (√Σ²) = {np.sqrt(sum(x**2 for x in sy)):.3f} %")
        st.caption("Erros aleatórios (ruído, resolução, vento) reduzem com mais leituras; sistemáticos (massa, distância, L, Δ, FSC) deslocam o GM igualmente em todas as leituras e NÃO aparecem nos resíduos.")

with T5:
    st.subheader("Diagnóstico automático")
    if res is None: st.info("Execute a prova para ver os alertas.")
    else:
        dg = ic.diagnose(dfl, plan, ship, res, lim, lim["tol"]); st.dataframe(dg, use_container_width=True)
        sev = dg.decisão.str.contains("SUSPENDER").any(); rep = dg.decisão.str.contains("REPETIR").any()
        (st.error if sev else st.warning if rep else st.success)("Decisão global: " + ("SUSPENDER o ensaio" if sev else "REPETIR leituras/bordo afetado" if rep else "ACEITAR após checklist"))
        if (dfl.amp_residual > lim["tol"]).any(): st.warning("Há leituras feitas com oscilação residual acima do limite.")
    st.markdown("**Checklist obrigatório (erros sistemáticos não detectáveis pelo ajuste):** pesar/calibrar cada peso · medir distâncias por dois métodos · sondar todos os tanques e corrigir FSC · "
                "conferir calado, densidade e Δ · amarras folgadas · registrar vento/corrente · comparar GM/KG com o previsto.")

# ======================================================================= PARTE III (análise) e VII
with T3:
    phi_a = st.slider("φ para análise [°]", 0.1, 5.0, 1.0, 0.1); tb = []
    for k, (Lk, rs) in enumerate(plan.pend):
        dl = Lk * np.tan(np.radians(phi_a)) * 1000
        tb.append({"Pêndulo": k + 1, "L (m)": Lk, "δ (mm)": dl, "φ de δ (°)": np.degrees(np.arctan(dl / 1000 / Lk)), "erro de leitura ±res/2 (°)": np.degrees(np.arctan((dl + rs / 2) / 1000 / Lk)) - phi_a, "erro relativo (%)": rs / 2 / dl * 100})
    if len(tb) > 1: st.write(f"Diferença entre instrumentos: |φ1 − φ2| = {abs(tb[0]['φ de δ (°)'] - tb[1]['φ de δ (°)']):.5f}°")
    st.dataframe(pd.DataFrame(tb).style.format(precision=4))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 3.5)); pp = np.linspace(0.1, 5, 60)
    for Lk in sorted({6.0, 12.0, 25.0, L1, L2}): a1.semilogy(pp, res_mm / 2 / (Lk * np.tan(np.radians(pp)) * 1000) * 100, label=f"L = {Lk:g} m")
    a1.set_xlabel("φ [°]"); a1.set_ylabel("erro relativo de leitura [%]"); a1.legend(); a1.grid(alpha=.3)
    LL = np.linspace(1, lim["L_max"], 40); a2.plot(LL, [ic.plan_precision(ship, replace(plan, pend=[(l_, res_mm)])) for l_ in LL]); a2.set_xlabel("L [m]"); a2.set_ylabel("σ_GM [%]"); a2.grid(alpha=.3); showfig(fig)
    s0 = ic.plan_precision(ship, replace(plan, pend=[(10.0, res_mm)])); Lreq = 10 * s0 / 1.0
    st.markdown(f"""**Discussão.** (1) δ = L·tanφ: a resolução fixa vira erro relativo res/(2δ), que cresce quando L é curto. (2) L longo amplia δ e reduz σ_GM ∝ 1/L.
(3) Limites: pé-direito/altura livre da embarcação (L máx. = {lim['L_max']} m aqui), amortecimento da bob, ar/vento, vibração e acesso. (4) Instrumentos independentes expõem erro de leitura, comprimento ou referência (razão de inclinações ≠ 1).
(5) Escolha: menor L tal que σ_GM ≤ 1 % no plano atual → L ≈ {Lreq:.1f} m {'(acima do limite: use mais momento)' if Lreq > lim['L_max'] else '(viável)'}; adotar dois pêndulos com comprimentos diferentes.""")

with T7:
    st.subheader("Comparação de configurações e proposta")
    ini = pd.DataFrame([dict(nome=n.split(" –")[0], n_g=p.n_g, m_w=round(p.m_w, 1), d=p.d, L1=L1, L2=L2) for n, p in cfgs.items()])
    cf = st.data_editor(ini, num_rows="dynamic", key="cfgs")
    w1, w2, w3 = st.columns(3); wp, wc, wt = w1.slider("Peso: precisão", 0.0, 1.0, 0.5), w2.slider("Peso: complexidade", 0.0, 1.0, 0.3), w3.slider("Peso: tempo", 0.0, 1.0, 0.2)
    if st.button("Avaliar configurações"):
        out = []
        for _, r_ in cf.iterrows():
            p = ic.Plan(int(r_.n_g), float(r_.m_w), float(r_.d), [(r_.L1, res_mm), (r_.L2, res_mm)]); e_ = replace(er, noise_mm=max(er.noise_mm, 0.3), wind_sigma=max(er.wind_sigma, 0.005))
            gs = ic.mc_gm(ship, p, e_, 80, 3); dft = ic.simulate_test(ship, p, e_, 0)
            viol = [m for ok_, m in [(2 * p.n_g * p.m_w <= lim["m_total"], "massa total"), (p.m_w <= lim["w_unit"], "massa unit."), (p.d <= lim["y_max"], "espaço"), (max(r_.L1, r_.L2) <= lim["L_max"], "L máx.")] if not ok_]
            out.append(dict(config=r_["nome"], phi_max=ic.predict(ship, p)["φ curva GZ (°)"].abs().max(), GM_medio=gs.mean(), vies_pct=(gs.mean() / gmr - 1) * 100, sigma_pct=gs.std() / gs.mean() * 100,
                            erro_total_pct=np.sqrt(((gs.mean() / gmr - 1) * 100) ** 2 + (gs.std() / gs.mean() * 100) ** 2), complexidade=2 * p.n_g * 8, tempo_s=dft.t_espera.sum(), violacoes=", ".join(viol)))
        o = pd.DataFrame(out); nz = lambda s: (s - s.min()) / (s.max() - s.min() + 1e-12)
        o["score"] = wp * nz(o.erro_total_pct) + wc * nz(o.complexidade) + wt * nz(o.tempo_s) + (o.violacoes != "") * 10; S.cfg_res = o
    if S.cfg_res is not None:
        o = S.cfg_res; st.dataframe(o.style.format(precision=3), use_container_width=True); win = o.loc[o.score.idxmin()]
        st.success(f"Configuração selecionada: **{win.config}** (menor score ponderado; sem violações = {win.violacoes == ''}).")
    st.markdown("**Proposta (justificativas)**"); items = ["Massa total inclinante", "Quantidade e distribuição dos pesos", "Distâncias de movimentação", "Faixa prevista de inclinação",
                                                          "Pêndulos (quantidade e comprimento)", "Sequência de movimentações", "Verificação de erros", "Prevenção de condições invalidantes"]
    txt = {i: st.text_area(i, key="t" + i, height=70) for i in items}
    ia = st.text_area("Registro das principais interações com a IA", height=120)
    md = f"# Relatório de planejamento – prova de inclinação\n\nΔ={ship.disp:.0f} t, T={ship.draft} m, KM={ship.KM:.3f} m, KG ref={ship.KG:.3f} m, GM ref={gm_ref:.3f} m\n\n## Plano\n{plan.n_g}×{plan.m_w} t por grupo, d={plan.d} m, pêndulos={plan.pend}\n\n" \
         + pred.to_markdown(index=False) + "\n\n" + "\n".join(f"## {k}\n{v}\n" for k, v in txt.items()) + (f"\n## Configurações\n{S.cfg_res.to_markdown(index=False)}\n" if S.cfg_res is not None else "") + f"\n## Interações com a IA\n{ia}\n"
    st.download_button("⬇️ Relatório (Markdown)", md, "relatorio_AP2.md")

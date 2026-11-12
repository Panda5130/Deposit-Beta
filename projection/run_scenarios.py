"""FFT scenario tests (+/-200 bp, instant or 4Q ramp) on each bank's champion over 12 quarters.

Usage: python projection/run_scenarios.py [--banks All|NAME ...] [--select SEL] [--no-charts]
Scenario CSVs (projection/scenarios/scn_*.csv) are generated here from the last actual FFT if missing
or if --regenerate is given. Outputs: projection/output/scenarios/scenario_projections.csv,
scenario_passthrough.csv and PNG charts in docs/figures/scenarios/.
Timing: the deposit data and the FFT file both end at T = 2026Q2 (guarded: the FFT end must equal the
bank-data end). Every scenario starts from the last actual FFT (3.6333) and the shock starts at h = 1
(2026Q3). Horizons are k = h = quarters after the last actual (k = 12 is 2029Q2).
Pass-through at k = (rate_k - rate_base_k) / full shock (+/-2.00); asymmetry = pass-through(up) -
|pass-through(down)| per timing (0 for a symmetric model).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import project as pj  # noqa: E402

bt, bp = pj.bt, pj.bp
ROOT = pj.ROOT
SCEN_DIR = HERE / "scenarios"
OUT_DIR = HERE / "output" / "scenarios"
FIG_DIR = ROOT / "docs" / "figures" / "scenarios"
H, SHOCK, RAMP_Q, HORIZONS = 12, 2.0, 4, (4, 8, 12)  # HORIZONS: k = h = quarters after the last actual
SCENARIOS = {  # name -> (sign, quarters to reach the full shock)
    "base": (0, 1), "up_instant": (1, 1), "up_ramp": (1, RAMP_Q),
    "down_instant": (-1, 1), "down_ramp": (-1, RAMP_Q)}
XLABEL = "Quarters after the last actual (0 = 2026Q2, actual FFT; shock from 2026Q3)"
COLORS = {"base": "#1f4e79", "up_instant": "#d9822b", "up_ramp": "#f2b97a",
          "down_instant": "#2e7d32", "down_ramp": "#8fc593"}


def last_fft(x="FFT"):
    s = pj.read_scenario(ROOT / "FFT_2011-2026.csv", x)
    bank = bp.to_periods(bp.read_csv(bp.DEFAULTS["dependents"])["quarter"]).max()
    bp.check_series_end(bank, s.index[-1], bp.DEFAULTS["dependents"], ROOT / "FFT_2011-2026.csv")
    return s.index[-1], float(s.iloc[-1])


def scenario_path(name, last_q, last):
    sign, n = SCENARIOS[name]
    steps = np.minimum(np.arange(1, H + 1) / n, 1.0)
    idx = pd.period_range(last_q + 1, periods=H, freq="Q")
    return pd.Series(last + sign * SHOCK * steps, index=idx, name="FFT")


def write_scenarios(last_q, last):
    for name in SCENARIOS:
        s = scenario_path(name, last_q, last)
        s = pd.concat([pd.Series([last], index=[last_q]), s])  # last actual row, ignored by project()
        pd.DataFrame({"FFT": s.values}, index=s.index.astype(str)).to_csv(SCEN_DIR / f"scn_{name}.csv")
    flat = pd.Series(last, index=pd.period_range(last_q + 1, periods=8, freq="Q"))  # 8Q flat sample scenario
    pd.DataFrame({"FFT": flat.values}, index=flat.index.astype(str)).to_csv(SCEN_DIR / "flat_8Q.csv")


def run(banks, select):
    summary, estimates = bt.load_candidates()
    source = bp.load_source(pj.DEFAULTS["dependents"], pj.DEFAULTS["independents"])
    if banks == ["All"]:
        banks = sorted(summary["bank_name"].astype(str).str.strip().unique())
    frames = []
    for bank in banks:
        p = pj.Projection.champion(bank, estimates, summary, source, select=select)
        for name in SCENARIOS:
            out = p.project(pj.read_scenario(SCEN_DIR / f"scn_{name}.csv"), freeze_trend=True)
            model = " | ".join(p.model)
            frames.append(out.assign(scenario=name, model=model)[
                ["bank_name", "model", "scenario", "quarter", "h", "FFT", "rate_pf_clean", "long_run_equilibrium"]]
                .rename(columns={"bank_name": "bank", "rate_pf_clean": "rate"})
                .assign(k=lambda d: d["h"]))  # quarters after the last actual (shock starts at h = 1)
    return pd.concat(frames, ignore_index=True)


def passthrough(proj):
    rows = []
    for bank, g in proj.groupby("bank"):
        base = g[g.scenario == "base"].set_index("k")["rate"]
        pt = {}
        for sc in SCENARIOS:
            if sc == "base":
                continue
            sg = g[g.scenario == sc].set_index("k")
            shock = SHOCK * SCENARIOS[sc][0]
            for h in HORIZONS:
                pt[sc, h] = (sg.loc[h, "rate"] - base[h]) / shock
                rows.append({"bank": bank, "scenario": sc, "k": h, "passthrough": pt[sc, h]})
        for timing in ("instant", "ramp"):
            for h in HORIZONS:  # up minus |down| response: 0 for a symmetric model
                rows.append({"bank": bank, "scenario": f"asym_{timing}", "k": h,
                             "passthrough": pt[f"up_{timing}", h] - pt[f"down_{timing}", h]})
    return pd.DataFrame(rows)


def charts(proj, pt):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    banks = sorted(proj.bank.unique())
    for bank in banks:
        g = proj[proj.bank == bank]
        fig, ax = plt.subplots(figsize=(11, 5))
        ax2 = ax.twinx()
        for sc in SCENARIOS:
            s = g[g.scenario == sc]
            ax.plot(s.k, s.rate, color=COLORS[sc], linewidth=2 if sc == "base" else 1.6,
                    linestyle="-" if "instant" in sc or sc == "base" else "--", label=sc)
            ax2.plot(s.k, s.FFT, color=COLORS[sc], linewidth=0.8, alpha=0.5, linestyle=":")
        ax.set_title(f"{bank}\n{g.model.iloc[0]}  (dotted: FFT, right axis)", fontsize=10)
        ax.set_xlabel(XLABEL)
        ax.set_ylabel("rate_pf_clean")
        ax2.set_ylabel("FFT")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="center left", bbox_to_anchor=(1.12, 0.5), frameon=False)
        fig.savefig(FIG_DIR / f"{bank.replace(' ', '_')}.png", dpi=120, bbox_inches="tight")
        plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5), sharey=True, constrained_layout=True)
    for ax, sc in zip(axes.ravel(), [s for s in SCENARIOS if s != "base"]):
        for bank in banks:
            g = proj[(proj.bank == bank) & (proj.scenario == sc)].set_index("k")["rate"]
            b = proj[(proj.bank == bank) & (proj.scenario == "base")].set_index("k")["rate"]
            ax.plot(g.index, (g - b) / (SHOCK * SCENARIOS[sc][0]), label=bank, linewidth=1.5)
        ax.set_title(sc.replace("_", " "), fontsize=11)
        ax.axvline(0, color="grey", linewidth=0.8, linestyle=":")
        ax.grid(True, alpha=0.3)
    fig.supxlabel(XLABEL, fontsize=10)
    axes[0, 0].set_ylabel("cumulative pass-through")
    axes[1, 0].set_ylabel("cumulative pass-through")
    axes[0, 1].legend(loc="center left", bbox_to_anchor=(1.02, 0), frameon=False, fontsize=9)
    fig.savefig(FIG_DIR / "all_banks_passthrough.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banks", nargs="+", default=["All"])
    ap.add_argument("--select", choices=bt.SELECT_CHOICES, default=bt.DEFAULT_SELECT)
    ap.add_argument("--regenerate", action="store_true", help="rewrite scenario CSVs from the last actual FFT")
    ap.add_argument("--no-charts", action="store_true")
    a = ap.parse_args(argv)
    if a.regenerate or not all((SCEN_DIR / f"scn_{n}.csv").exists() for n in SCENARIOS):
        write_scenarios(*last_fft())
    proj = run(a.banks, a.select)
    pt = passthrough(proj)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    proj.to_csv(OUT_DIR / "scenario_projections.csv", index=False)
    pt.to_csv(OUT_DIR / "scenario_passthrough.csv", index=False)
    if not a.no_charts:
        charts(proj, pt)
    print(pt.pivot_table(index="bank", columns=["scenario", "k"], values="passthrough").round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())

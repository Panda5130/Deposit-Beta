"""Gregory-Hansen (1996) residual-based cointegration tests with one unknown break.

For every candidate break tau in the trimmed range [0.15T, 0.85T] the cointegrating regression
is fitted by OLS with a shift dummy D_t = 1{t > tau}, and the residuals are tested for a unit
root. The test statistic is the smallest (most negative) value over all tau; the break date
reported is the first quarter with D = 1 at the tau that attains it (the Zivot-Andrews convention).

Models (m = 1 regressor, x = FFT):
    C     level shift            y = c1 + c2 D + a x
    C/T   level shift with trend y = c1 + c2 D + b t + a x
    C/S   regime shift           y = c1 + c2 D + a1 x + a2 x D
    C/S/T regime shift and trend y = c1 + c2 D + b t + a1 x + a2 x D   (Gregory and Hansen 1996b)

Statistics:
    ADF*  min over tau of the ADF t on the residuals (no constant; lags by AIC, max 4)
    Zt*   min over tau of the Phillips Zt (Bartlett kernel, Newey-West bandwidth)
    Za*   min over tau of the Phillips Z-alpha

Critical values: the asymptotic ones in Gregory and Hansen (1996), Table 1, m = 1, and
finite-sample ones for T = 62 simulated here under the null (independent random walks for y
and x, the same trimming and lag rule), because 62 quarters is short for asymptotic values.
"""

import numpy as np
import pandas as pd

MODELS = ["C", "C/T", "C/S", "C/S/T"]
TRIM = 0.15
MAX_LAG = 4
# Gregory and Hansen (1996), Table 1, m = 1: (1%, 5%, 10%). C/S/T from Gregory and Hansen (1996b).
ASYMPTOTIC_CV = {
    "ADF": {"C": (-5.13, -4.61, -4.34), "C/T": (-5.45, -4.99, -4.72), "C/S": (-5.47, -4.95, -4.68),
            "C/S/T": (-6.02, -5.50, -5.24)},
    "Za": {"C": (-50.07, -40.48, -36.19), "C/T": (-57.28, -47.96, -43.22), "C/S": (-57.17, -47.04, -41.85),
           "C/S/T": (-69.37, -58.58, -53.31)},
}
ASYMPTOTIC_CV["Zt"] = ASYMPTOTIC_CV["ADF"]


def design(x, model, tau):
    """Regressors of the cointegrating regression for a break after position tau (0-based)."""
    n = len(x)
    d = (np.arange(n) > tau).astype(float)
    cols = [np.ones(n), d]
    if model in ("C/T", "C/S/T"):
        cols.append(np.arange(1, n + 1, dtype=float))
    cols.append(x)
    if model in ("C/S", "C/S/T"):
        cols.append(x * d)
    return np.column_stack(cols)


def ols_resid(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta, beta


def adf_t(e, max_lag=MAX_LAG):
    """ADF t on residuals, no deterministic terms, lag by AIC over a common sample."""
    de = np.diff(e)
    n = len(de) - max_lag
    best = None
    for p in range(max_lag + 1):
        Y = de[max_lag:]
        cols = [e[max_lag:-1]] + [de[max_lag - j:-j] for j in range(1, p + 1)]
        X = np.column_stack(cols)
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        u = Y - X @ b
        aic = n * np.log(u @ u / n) + 2 * X.shape[1]
        if best is None or aic < best[0]:
            best = (aic, p)
    p = best[1]
    # Refit the chosen lag on all available observations.
    Y = de[p:]
    X = np.column_stack([e[p:-1]] + [de[p - j:-j] for j in range(1, p + 1)])
    b, *_ = np.linalg.lstsq(X, Y, rcond=None)
    u = Y - X @ b
    s2 = u @ u / (len(Y) - X.shape[1])
    se = np.sqrt(s2 * np.linalg.inv(X.T @ X)[0, 0])
    return b[0] / se, p


def phillips(e):
    """Phillips Z-alpha and Zt on residuals (AR(1) without constant, Bartlett long-run variance)."""
    y1, y0 = e[1:], e[:-1]
    rho = (y0 @ y1) / (y0 @ y0)
    u = y1 - rho * y0
    n = len(u)
    bw = int(np.floor(4 * (n / 100) ** (2 / 9)))
    gamma0 = u @ u / n
    lam = sum((1 - j / (bw + 1)) * (u[j:] @ u[:-j]) / n for j in range(1, bw + 1))
    s2 = gamma0 + 2 * lam
    rho_star = rho - lam / ((y0 @ y0) / n)
    za = n * (rho_star - 1)
    zt = (rho_star - 1) / np.sqrt(s2 / (y0 @ y0))
    return za, zt


def breaks(n):
    return range(int(np.floor(TRIM * n)) - 1, int(np.floor((1 - TRIM) * n)))


def gh_stats(y, x, model):
    """{stat: (value, tau)} for the three GH statistics, minimised over breaks."""
    out = {"ADF": (np.inf, None, None), "Zt": (np.inf, None, None), "Za": (np.inf, None, None)}
    for tau in breaks(len(y)):
        e, _ = ols_resid(y, design(x, model, tau))
        t, p = adf_t(e)
        za, zt = phillips(e)
        for k, v, lag in (("ADF", t, p), ("Zt", zt, None), ("Za", za, None)):
            if v < out[k][0]:
                out[k] = (v, tau, lag)
    return out


def simulate_cv(n, model, reps=2000, seed=20261031):
    """Finite-sample (1%, 5%, 10%) critical values under no cointegration."""
    rng = np.random.default_rng(seed + MODELS.index(model))
    draws = {"ADF": [], "Zt": [], "Za": []}
    for _ in range(reps):
        y = np.cumsum(rng.standard_normal(n))
        x = np.cumsum(rng.standard_normal(n))
        s = gh_stats(y, x, model)
        for k in draws:
            draws[k].append(s[k][0])
    return {k: tuple(np.quantile(v, [0.01, 0.05, 0.10])) for k, v in draws.items()}


def run(data, y, x, cv_sim):
    """One row per (model, statistic) for one bank's data (indexed by quarter)."""
    rows = []
    yv, xv = data[y].to_numpy(float), data[x].to_numpy(float)
    for model in MODELS:
        stats = gh_stats(yv, xv, model)
        _, beta = ols_resid(yv, design(xv, model, stats["ADF"][1]))
        for k, (value, tau, lag) in stats.items():
            asy, sim = ASYMPTOTIC_CV[k][model], cv_sim[model][k]
            rows.append({
                "model": model, "statistic": f"{k}*", "value": value,
                # First quarter with D = 1, the same convention as Zivot-Andrews in diagnostics/.
                "break_quarter": str(data.index[tau + 1]), "last_pre_break_quarter": str(data.index[tau]),
                "adf_lags": lag, "cv_1_asy": asy[0], "cv_5_asy": asy[1], "cv_10_asy": asy[2],
                "cv_1_sim": sim[0], "cv_5_sim": sim[1], "cv_10_sim": sim[2],
                "reject_5_asy": value < asy[1], "reject_5_sim": value < sim[1],
                # Cointegrating-regression coefficients at the ADF* break (const, shift, [trend], x, [x*D]).
                "coefs_at_adf_break": " ".join(f"{b:.4f}" for b in beta) if k == "ADF" else "",
            })
    return rows


def adf_path(data, y, x, model):
    """ADF t at every candidate break, for charts."""
    yv, xv = data[y].to_numpy(float), data[x].to_numpy(float)
    return pd.Series({str(data.index[tau + 1]): adf_t(ols_resid(yv, design(xv, model, tau))[0])[0]
                      for tau in breaks(len(yv))})

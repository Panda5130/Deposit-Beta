"""Asymmetric (NARDL-style) variant of every ECM that passed the cointegration screen.

Usage (all arguments optional; defaults point at the files in this folder):
    python "ECM asymmetric variants.py" [-i MODEL_SELECTION_CSV] [--dependents FILE]
        [--independents FILE] [--y COLUMN] [--x COLUMN] [--alpha 0.05] [--out-dir DIR]

No new cointegration screen and no change to the original models. The input is the list of
specifications that passed the screen ("ECM model selection results.csv"), each with its
full pre-screen short-run lag set. The original cointegration, model-selection,
parameter-selection and estimation outputs are only read: their SHA-256 hashes are taken
before the run and checked after it, and the run fails if any of them changed.

One fully split variant per survivor:

    dy_t = lam+ ect+_{t-1} + lam- ect-_{t-1}
           + sum_i (g+_i dFFT+_{t-i} + g-_i dFFT-_{t-i}) + sum_j (p+_j dy+_{t-j} + p-_j dy-_{t-j}) + e_t
    ect_{t-1} = y_{t-1} - c - delta*trend_t - theta+ FFT+_{t-1} - theta- FFT-_{t-1}

    dv+ = max(dv, 0), dv- = min(dv, 0)          (v = FFT or y; no summation)
    FFT+_t = FFT_0 + sum_{s<=t} max(dFFT_s, 0)  (partial sums: the level of FFT is itself a running
    FFT-_t =         sum_{s<=t} min(dFFT_s, 0)   sum of its changes, so FFT+ + FFT- = FFT exactly;
                                                  the start level goes in FFT+ so that models
                                                  without a constant nest the symmetric one)
    ect+ = max(ect, 0), ect- = min(ect, 0)

The trend enters as in the symmetric one-step ECM (trend_t, counted from the first quarter),
so lam+ = lam- gives back the linear form exactly. Deterministic terms follow the survivor's
trend type, as in "ECM estimation.py".

Estimation (Enders-Siklos TAR form):
    1. OLS of the linear one-step ECM with split levels and short-run terms and a single lambda.
       This gives theta+-, the starting values and the first regime indicator 1(ect > 0).
    2. With the indicator held fixed, lam+, lam-, c, delta, theta+-, and the short-run
       coefficients by nonlinear least squares (smooth for a fixed indicator; standard errors
       from the Jacobian, s^2 (J'J)^-1).
    3. Recompute the indicator from the new ect and repeat until it stops changing (at most
       MAX_PASSES = 20). If the indicator returns to one already fitted (a cycle, usually
       quarters with ect near 0 flipping back and forth) or the cap is hit, the pass with the
       lowest sum of squared residuals is kept and the form records "indicator cycled" / "not
       converged". A regime with fewer than MIN_REGIME (6) quarters keeps lambda symmetric (as
       in model_form/challengers.py).

Pruning, with + and - kept together:
    short-run pairs (dFFT+_{t-i}, dFFT-_{t-i}) and (dy+_{t-j}, dy-_{t-j}): from the full lag set,
        drop the pair with the highest joint Wald-F p-value while it is >= alpha, refit, repeat.
    lam+- and theta+-: cannot be dropped (the model must error-correct and keep its long run),
        so "both or none" applies to the asymmetry: when a Wald test does not reject lam+ = lam-
        (then theta+ = theta-) at alpha, the pair collapses to one symmetric term, the model is
        refit and the short-run pairs are checked again.

Outputs (new files only):
    ECM asymmetric estimation results.csv     the "ECM estimation results.csv" schema plus asymmetric;
                                              test_name is "<survivor test_name> | asymmetric".
                                              With lam split the rows are ect_pos.L1 (lam+),
                                              ect_neg.L1 (lam-), the short-run terms and the
                                              long-run "LR: const/trend/FFT_pos/FFT_neg"; otherwise
                                              the linear form (rate_pf_clean.L1, FFT_pos.L1, ...)
                                              plus LR rows by the delta method, as for the originals.
    asymmetric estimation result summary.csv  the "estimation result summary.csv" schema plus asymmetric
    ECM asymmetric tests.csv                  per variant: Wald symmetry tests (lambda, theta,
                                              sum gamma dFFT, sum phi dy), the decision, and the
                                              fit diagnostics (form, passes, regime sizes, pairs kept)

The module is also imported by MAE_Backtesting/backtest.py, which refits the variants at
every start date with fit().
"""

import argparse
import hashlib
import importlib.util
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import optimize, stats

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import bank_plots as bp  # noqa: E402


def load_module(path, name):
    # The file names have spaces, so they can't be imported with a plain import.
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


est = load_module(HERE / "ECM estimation.py", "ecm_estimation")
ct = est.ct

POS, NEG = bp.POS, bp.NEG
LAMBDA_POS, LAMBDA_NEG = "ect_pos.L1", "ect_neg.L1"
MIN_REGIME, MAX_PASSES, ALPHA = 6, 20, 0.05
ASYM_TAG = " | asymmetric"
INPUT_NAME = "ECM model selection results.csv"
OUTPUT_NAME = "ECM asymmetric estimation results.csv"
SUMMARY_NAME = "asymmetric estimation result summary.csv"
TESTS_NAME = "ECM asymmetric tests.csv"
GROUP_KEYS = est.GROUP_KEYS
OUTPUT_COLUMNS = est.OUTPUT_COLUMNS + ["asymmetric"]
SUMMARY_COLUMNS = est.SUMMARY_COLUMNS + ["asymmetric"]
# Original outputs that this script must leave untouched (hashed before and after the run).
PROTECTED = ["Co-integration_results.csv", "co-integration_respecification_results.csv",
             "ECM model selection results.csv", "ECM param selection results.csv",
             "ECM estimation results.csv", "estimation result summary.csv"]


# Model pieces ---------------------------------------------------------------------------------
def split_levels(levels):
    return [f"{v}{s}" for v in levels for s in (POS, NEG)]


def expand_pairs(pairs):
    """[(var, lag)] base pairs -> the split short-run terms [(var_pos, lag), (var_neg, lag)]."""
    return [(f"{v}{s}", k) for v, k in pairs for s in (POS, NEG)]


def pair_names(var, lag):
    return f"D.{var}{POS}.L{lag}", f"D.{var}{NEG}.L{lag}"


def terms_of(y, det, levels, short_run):
    return det + [f"{y}.L1"] + [f"{v}.L1" for v in levels] + [f"D.{v}.L{k}" for v, k in short_run]


def design(data, y, terms):
    """dy and the regressors for `terms`, built by bank_plots.regressor, complete rows only."""
    X = pd.concat({t: bp.regressor(data, t) for t in terms}, axis=1)
    return pd.concat([data[y].diff().rename("dy"), X], axis=1).dropna()


def fit_linear(data, y, det, levels, short_run):
    """OLS of the linear one-step ECM. Same columns, rows and order as ECM estimation.fit_one_step,
    with split levels and short-run terms rebuilt from the base series."""
    terms = terms_of(y, det, levels, short_run)
    frame = design(data, y, terms)
    return sm.OLS(frame["dy"], frame[terms]).fit()


@dataclass
class AsymFit:
    """The TAR one-step ECM with lambda split by the sign of ect (fit_tar).

    Quacks like the statsmodels results the backtests use: params, pvalues, tvalues, resid,
    nobs, df_resid and cov_params(). params holds the forecasting terms (ect_pos.L1, ect_neg.L1
    and the short-run terms); the long-run part is in lr and in the "LR: ..." entries of full.
    """
    full: pd.Series  # every estimated parameter: ect_pos.L1, ect_neg.L1, LR: <det/levels>, short run
    cov: pd.DataFrame
    resid: pd.Series
    df_resid: int
    y: str
    det: list
    levels: list
    form: str = "lambda split"
    converged: bool = True
    passes: int = 0
    n_pos: int = 0
    n_neg: int = 0
    lr: dict = field(default_factory=dict)

    @property
    def params(self):
        return self.full[[n for n in self.full.index if not n.startswith("LR: ")]]

    @property
    def bse_full(self):
        return pd.Series(np.sqrt(np.clip(np.diag(self.cov.values), 0, None)), index=self.full.index)

    @property
    def tvalues_full(self):
        return self.full / self.bse_full

    @property
    def pvalues_full(self):
        return pd.Series(2 * stats.t.sf(np.abs(self.tvalues_full), self.df_resid), index=self.full.index)

    @property
    def tvalues(self):
        return self.tvalues_full[self.params.index]

    @property
    def pvalues(self):
        return self.pvalues_full[self.params.index]

    @property
    def nobs(self):
        return float(len(self.resid))

    def cov_params(self):
        return self.cov

    @property
    def ect_weights(self):
        """ect.L1 as a weighted sum of regressors: y.L1 - c - delta*trend - sum theta * level.L1."""
        w = {f"{self.y}.L1": 1.0}
        for name, theta in self.lr.items():
            w[name if name in ("const", "trend") else f"{name}.L1"] = -theta
        return w

    def long_run_rows(self):
        """[(LR: name, theta, t, p)] in the layout of ECM estimation.long_run_rows."""
        names = [n for n in self.full.index if n.startswith("LR: ")]
        return [(n, float(self.full[n]), float(self.tvalues_full[n]), float(self.pvalues_full[n])) for n in names]


def is_tar(res):
    return isinstance(res, AsymFit)


def coefficients(res):
    """(estimates, covariance) over every estimated parameter, OLS or TAR."""
    return (res.full, res.cov) if is_tar(res) else (res.params, res.cov_params())


def long_run_rows(res, y, det, levels):
    return res.long_run_rows() if is_tar(res) else est.long_run_rows(res, y, det, levels)


def fit_tar(data, y, det, levels, short_run, min_regime=MIN_REGIME, max_passes=MAX_PASSES):
    """lambda split by the sign of ect, fitted by NLS with the regime indicator fixed and iterated.

    Returns an AsymFit, or the linear OLS fit (single lambda) when a regime has fewer than
    min_regime quarters; that result gets a `form` attribute saying why.
    """
    lin = fit_linear(data, y, det, levels, short_run)
    lam_name, d_terms = f"{y}.L1", det + [f"{v}.L1" for v in levels]
    s_terms = [f"D.{v}.L{k}" for v, k in short_run]
    frame = design(data, y, [lam_name] + d_terms + s_terms)
    dy, y1 = frame["dy"].to_numpy(), frame[lam_name].to_numpy()
    D, S = frame[d_terms].to_numpy(), frame[s_terms].to_numpy().reshape(len(frame), len(s_terms))
    nd, ns = D.shape[1], S.shape[1]
    lam = float(lin.params[lam_name])
    x0 = np.concatenate([[lam, lam], -lin.params[d_terms].to_numpy() / lam, lin.params[s_terms].to_numpy()])

    def unpack(p):
        return p[0], p[1], p[2:2 + nd], p[2 + nd:]

    def jac_fitted(p, ind):
        lp, ln, phi, _ = unpack(p)
        e = y1 - D @ phi
        lam_t = np.where(ind, lp, ln)
        return np.column_stack([np.where(ind, e, 0.0), np.where(ind, 0.0, e), -lam_t[:, None] * D, S])

    def resid(p, ind):
        lp, ln, phi, g = unpack(p)
        return dy - (np.where(ind, lp, ln) * (y1 - D @ phi) + S @ g)

    ind = (y1 - D @ x0[2:2 + nd]) > 0
    passes, converged, status, seen = 0, False, "not converged in %d passes" % max_passes, {}
    while passes < max_passes:
        n_pos = int(ind.sum())
        if min(n_pos, len(ind) - n_pos) < min_regime:
            lin.form = f"symmetric lambda (regime of {min(n_pos, len(ind) - n_pos)} quarters < {min_regime})"
            lin.n_pos, lin.n_neg = n_pos, len(ind) - n_pos
            return lin
        passes += 1
        sol = optimize.least_squares(resid, x0, jac=lambda p, i: -jac_fitted(p, i), args=(ind,), method="lm",
                                     xtol=1e-12, ftol=1e-12, gtol=1e-12)
        x0 = sol.x
        seen[ind.tobytes()] = (float(sol.fun @ sol.fun), x0.copy(), ind.copy())
        new = (y1 - D @ x0[2:2 + nd]) > 0
        if (new == ind).all():
            converged = True
            break
        if new.tobytes() in seen:
            status = "indicator cycled"
            break
        ind = new
    if not converged:  # keep the pass with the lowest sum of squared residuals
        _, x0, ind = min(seen.values(), key=lambda v: v[0])
    names = [LAMBDA_POS, LAMBDA_NEG] + [f"LR: {t.removesuffix('.L1')}" for t in d_terms] + s_terms
    r = resid(x0, ind)
    n, k = len(r), len(x0)
    J = jac_fitted(x0, ind)
    cov = (r @ r / (n - k)) * np.linalg.pinv(J.T @ J)
    full = pd.Series(x0, index=names)
    lr = {t.removesuffix(".L1"): float(v) for t, v in zip(d_terms, x0[2:2 + nd])}
    return AsymFit(full, pd.DataFrame(cov, index=names, columns=names), pd.Series(r, index=frame.index), n - k,
                   y, list(det), list(levels),
                   "lambda split" if converged else f"lambda split ({status}; lowest-SSR pass kept)",
                   converged, passes, int(ind.sum()), int((~ind).sum()), lr)


def fit(data, y, det, levels, short_run, split_lambda):
    """The variant at its current form: TAR (lambda split) or linear OLS (single lambda)."""
    if split_lambda:
        return fit_tar(data, y, det, levels, short_run)
    return fit_linear(data, y, det, levels, short_run)


def wald(res, restrictions):
    """Wald F test of R b = 0, restrictions = [{name: weight}] -> (F, p, q)."""
    b, cov = coefficients(res)
    R = np.array([[r.get(n, 0.0) for n in b.index] for r in restrictions], dtype=float)
    missing = {n for r in restrictions for n in r} - set(b.index)
    if missing:
        raise KeyError(f"not in the model: {', '.join(sorted(missing))}")
    v = R @ b.to_numpy()
    q = len(restrictions)
    F = float(v @ np.linalg.solve(R @ cov.to_numpy() @ R.T, v)) / q
    return F, float(stats.f.sf(F, q, res.df_resid)), q


def lambda_restriction(res, y):
    return [{LAMBDA_POS: 1.0, LAMBDA_NEG: -1.0}]


def theta_restriction(res, x):
    if is_tar(res):  # theta+- are parameters
        return [{f"LR: {x}{POS}": 1.0, f"LR: {x}{NEG}": -1.0}]
    return [{f"{x}{POS}.L1": 1.0, f"{x}{NEG}.L1": -1.0}]  # theta = -b/lambda with one lambda: b+ = b-


def sum_restriction(pairs, var):
    r = {}
    for v, k in pairs:
        if v == var:
            p, n = pair_names(v, k)
            r[p], r[n] = 1.0, -1.0
    return [r] if r else None


def prune_pairs(data, y, det, levels, pairs, split_lambda, alpha=ALPHA):
    """Drop short-run (+, -) pairs by joint Wald-F p-value, largest first, while p >= alpha."""
    pairs = list(pairs)
    while True:
        res = fit(data, y, det, levels, expand_pairs(pairs), split_lambda)
        if not pairs:
            return res, pairs
        pvals = {pair: wald(res, [{pair_names(*pair)[0]: 1.0}, {pair_names(*pair)[1]: 1.0}])[1] for pair in pairs}
        worst = max(pvals, key=pvals.get)
        if pvals[worst] < alpha:
            return res, pairs
        pairs.remove(worst)


@dataclass
class Variant:
    res: object
    det: list
    levels: list
    pairs: list
    split_lambda: bool
    split_theta: bool
    tests: list


def build_variant(data, y, x, det, short_run, alpha=ALPHA):
    """Fully split variant of one survivor, pruned with + and - kept together (module docstring)."""
    split_lambda, split_theta, pairs = True, True, list(short_run)
    tests = {}
    while True:
        levels = split_levels([x]) if split_theta else [x]
        res, pairs = prune_pairs(data, y, det, levels, pairs, split_lambda, alpha)
        if split_lambda:
            if not is_tar(res):  # a regime was too small: lambda stays symmetric
                tests["lambda"] = dict(stat=np.nan, df=np.nan, p_value=np.nan, decision=f"symmetric: {res.form}",
                                       tested_on="split model after pair pruning")
                split_lambda = False
            else:
                F, p, q = wald(res, lambda_restriction(res, y))
                keep = p < alpha
                tests["lambda"] = dict(stat=F, df=q, p_value=p, tested_on="split model after pair pruning",
                                       decision="asymmetric kept" if keep else "collapsed to symmetric")
                if not keep:
                    split_lambda = False
                    continue
        if split_theta:
            F, p, q = wald(res, theta_restriction(res, x))
            keep = p < alpha
            tests["theta"] = dict(stat=F, df=q, p_value=p, decision="asymmetric kept" if keep else "collapsed to symmetric",
                                  tested_on=f"lambda {'split' if split_lambda else 'symmetric'}, after pair pruning")
            if not keep:
                split_theta = False
                continue
        break
    for name, var in (("sum gamma dFFT", x), ("sum phi dy", y)):
        r = sum_restriction(pairs, var)
        n_pairs = sum(v == var for v, _ in pairs)
        if r is None:
            tests[name] = dict(stat=np.nan, df=np.nan, p_value=np.nan, tested_on="final model",
                               decision="no pair survived pruning")
        else:
            F, p, q = wald(res, r)
            tests[name] = dict(stat=F, df=q, p_value=p, tested_on=f"final model ({n_pairs} pair(s))",
                               decision="asymmetric at 5%" if p < alpha else "not rejected at 5%")
    rows = [{"test": k, **v} for k, v in tests.items()]
    return Variant(res, det, levels, pairs, split_lambda, split_theta, rows)


def build_pruned(data, y, x, name, det, short_run, alpha=ALPHA):
    """build_variant, then the deterministic-term rule (deterministic_pruning.prune).

    A dropped term rebuilds the variant from the full short-run pair set, so the pair pruning
    and the +/- collapse run again with the remaining deterministic terms. The variant is
    always kept and keeps its keys. Returns (Variant, log rows).
    """
    def refit(d):
        return build_variant(data, y, x, list(d), short_run, alpha)

    def pvalue_of(v, term):
        row = est.dp.tested_row(name[1], name[3], term, lambda_split=is_tar(v.res))
        rows = {r[0]: r[3] for r in estimate_rows(v.res, y, v.det, v.levels)}
        return float(rows[row]), row

    v, det, log = est.dp.prune(tuple(name), list(det), refit, pvalue_of, alpha, asymmetric=True)
    return v, log


def estimate_rows(res, y, det, levels):
    """[(term, coef, t, p)]: the fitted terms, then the long-run rows."""
    if is_tar(res):
        fitted = list(zip(res.params.index, res.params, res.tvalues, res.pvalues))
    else:
        fitted = list(zip(res.params.index, res.params, res.tvalues, res.pvalues))
    return fitted + long_run_rows(res, y, det, levels)


# Script --------------------------------------------------------------------------------------
def file_hashes(folder, names=PROTECTED):
    return {n: hashlib.sha256((Path(folder) / n).read_bytes()).hexdigest() if (Path(folder) / n).exists() else None
            for n in names}


def survivors(selected, y, xs):
    """(keys, det, short_run base pairs) for every screened spec that is an ECM."""
    out, skipped = [], []
    for keys, group in selected.groupby(GROUP_KEYS, sort=False):
        try:
            _, _, short_run = est.ecm_spec(keys[1], group["term"].dropna(), y, xs)
        except ValueError as e:
            skipped.append((keys, str(e)))
            continue
        out.append((keys, est.test_deterministics(keys[3]), short_run))
    return out, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description="Asymmetric variant of every screened ECM.")
    parser.add_argument("-i", "--input", default=HERE / INPUT_NAME, help="ECM model selection results.csv")
    parser.add_argument("--dependents", default=HERE / "consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted.csv")
    parser.add_argument("--independents", default=HERE / "FFT_2011-2026.csv")
    parser.add_argument("--y", default="rate_pf_clean")
    parser.add_argument("--x", default="FFT")
    parser.add_argument("--group-column", default="bank_name")
    parser.add_argument("--alpha", type=float, default=ALPHA)
    parser.add_argument("--out-dir", default=HERE)
    parser.add_argument("--prune-deterministics", dest="prune_deterministics", action="store_true", default=True,
                        help="deterministic-term rule of deterministic_pruning.py (default); writes '(det pruned)' files")
    parser.add_argument("--no-prune-deterministics", dest="prune_deterministics", action="store_false",
                        help="old behaviour: deterministic terms follow the survivor's trend type")
    parser.add_argument("--pruning-log", default=HERE / est.dp.LOG_NAME)
    args = parser.parse_args(argv)

    out = Path(args.out_dir)
    prune = args.prune_deterministics
    names = [OUTPUT_NAME, SUMMARY_NAME, TESTS_NAME]
    targets = [out / (est.pruned_name(n) if prune else n) for n in names]
    protected = PROTECTED + (names + [est.pruned_name(n) for n in (est.OUTPUT_NAME, est.SUMMARY_NAME)]
                             if prune else [])
    if any(t.name in PROTECTED or (prune and t.name in names) for t in targets):
        ct.err("refusing to write over an original output")
        return 1
    before = file_hashes(HERE, protected)
    try:
        selected = pd.read_csv(args.input)
        source = ct.merge_sources(ct.read_table(args.dependents), ct.read_table(args.independents), None, None, "Q")
    except (FileNotFoundError, ValueError) as e:
        ct.err(e)
        return 1
    specs, skipped = survivors(selected, args.y, [args.x])
    print(f"{len(specs)} screened ECM specification(s); {len(skipped)} screened test(s) are not ECMs")

    rows, summary, tests, data_cache = [], [], [], {}
    built, order, log = {}, [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for keys, det, short_run in specs:
            bank = keys[0]
            name = (bank, keys[1] + ASYM_TAG, keys[2], keys[3])
            try:
                if bank not in data_cache:
                    _, subset = next(ct.select_groups(source, {"group_column": args.group_column, "group_value": bank}))
                    data_cache[bank] = ct.prepare_data(subset, args.y, [args.x])
                if prune:
                    v, spec_log = build_pruned(data_cache[bank], args.y, args.x, name, det, short_run, args.alpha)
                    final = name
                    log += spec_log
                else:
                    v, final = build_variant(data_cache[bank], args.y, args.x, det, short_run, args.alpha), name
            except Exception as e:
                ct.err(f"{' / '.join(map(str, name))}: {e}")
                continue
            order.append(name)
            built[name] = (v, final, short_run)
    if prune:
        n_pruned = len({tuple(r[c] for c in est.dp.SPEC) for r in log if r["action"].startswith("dropped")})
        print(f"deterministic pruning: {len(order)} variant(s), {n_pruned} with a term dropped; "
              f"log -> {Path(args.pruning_log).name}")
    for name0 in order:
        v, name, short_run = built[name0]
        if v is None:
            continue
        for term, coef, t, p in estimate_rows(v.res, args.y, v.det, v.levels):
            rows.append([*name, term, coef, t, p, True])
        summary.append([*name, float(np.mean(np.abs(v.res.resid))), True])
        diag = {"form": getattr(v.res, "form", "single lambda"), "converged": getattr(v.res, "converged", np.nan),
                "passes": getattr(v.res, "passes", np.nan), "n_ect_pos": getattr(v.res, "n_pos", np.nan),
                "n_ect_neg": getattr(v.res, "n_neg", np.nan), "lambda_split": v.split_lambda,
                "theta_split": v.split_theta,
                "pairs_start": " ".join(f"D.{a}.L{k}" for a, k in short_run),
                "pairs_kept": " ".join(f"D.{a}.L{k}" for a, k in v.pairs), "n_params": len(v.res.params)
                + (len(v.res.lr) if is_tar(v.res) else 0), "nobs": int(v.res.nobs)}
        tests += [{**dict(zip(GROUP_KEYS, name)), **t, **diag} for t in v.tests]

    after = file_hashes(HERE, protected)
    changed = [n for n in protected if before[n] != after[n]]
    if changed:
        ct.err(f"original outputs changed during the run: {', '.join(changed)}")
        return 1
    try:
        pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(targets[0], index=False)
        pd.DataFrame(summary, columns=SUMMARY_COLUMNS).to_csv(targets[1], index=False)
        pd.DataFrame(tests).to_csv(targets[2], index=False)
        if prune:
            est.dp.write_log(args.pruning_log, log, asymmetric=True)
    except OSError as e:
        ct.err(f"could not write output: {e}")
        return 1
    final = file_hashes(HERE, protected)
    assert final == before, "original outputs changed"
    print(f"{len(summary)} variant(s) written to {targets[0].name}; originals unchanged (SHA-256 checked)")
    return 0 if rows else 2


if __name__ == "__main__":
    sys.exit(main())

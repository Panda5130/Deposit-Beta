"""Deterministic-term pruning for the one-step ECMs (step 3) and their asymmetric variants.

Order: the cointegration screen comes first (its outputs are only read, never rerun); this
pruning comes after it and after the short-run pruning. There is no cointegration re-check.

Rule (model owner, 2026-11-11):
    1. After the short-run pruning, test the trend; if p >= alpha (0.05) drop it and refit
       (short-run pruning runs again from the step-2 set). Then test the constant the same way.
       Repeat until every remaining deterministic term has p < alpha. The model is always kept.
    2. Which row carries the test:
           EG_LongRun and Johansen VECM    the long-run row "LR: const" / "LR: trend" (delta method)
           ARDL case 2 const, case 4 trend the long-run row (the term is restricted to the long run)
           ARDL other (case 3/5 terms)     the one-step OLS coefficient "const" / "trend"
           asymmetric TAR form (lam split) "LR: ..." (the only row it has)
    3. The model keeps its keys (bank, test_name, IC/selected lag, trend type): the trend type is
       the QUALIFYING case, the one the cointegration screen passed. The remaining deterministic
       form is in the fitted terms and in the log. Whether the remaining form was itself
       screened is NOT looked up; form_differs_from_qualifying_test only flags that it is not the
       qualifying case (for the documentation's limitations section).

Every test is a row of the pruning log (LOG_COLUMNS).

Dry run (no fitting), from the existing estimation outputs:
    python deterministic_pruning.py [--estimates CSV] [--asym-estimates CSV]
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ALPHA = 0.05
SCREEN_NAME = "ECM model selection results.csv"
LOG_NAME = "deterministic_pruning_log.csv"
SPEC = ["bank_name", "test_name", "IC/selected lag", "trend type"]
LOG_COLUMNS = SPEC + ["asymmetric", "term", "p_value", "tested_on", "qualifying_case", "action",
                      "remaining_form", "form_differs_from_qualifying_test"]
ASYM_TAG = " | asymmetric"
ARDL_RE = re.compile(r"^ARDL bounds F \(ARDL\((?P<lags>[\d,]+)\), case (?P<case>\d)\)$")
ORDER = ("trend", "const")  # trend first, then const


def base_test_name(test_name):
    return str(test_name).removesuffix(ASYM_TAG)


def family(test_name):
    name = base_test_name(test_name)
    for fam in ("EG", "Johansen", "ARDL"):
        if name.startswith(fam):
            return fam
    raise ValueError(f"unknown test family: {test_name}")


def ardl_case(test_name):
    m = ARDL_RE.match(base_test_name(test_name))
    if not m:
        raise ValueError(f"not an ARDL bounds test name: {test_name}")
    return int(m["case"])


def case_of(test_name, trend_type):
    """Short label of the qualifying case: 'ct', 'det_order 1', 'case 4', ..."""
    fam = family(test_name)
    if fam == "ARDL":
        return f"case {ardl_case(test_name)}"
    if fam == "Johansen":
        return " ".join(str(trend_type).split()[:2])
    return str(trend_type).split()[0]


def det_of(trend_type):
    """Deterministic terms of the qualifying case (trend type label)."""
    label = str(trend_type)
    if label.startswith("det_order"):
        return {-1: [], 0: ["const"], 1: ["const", "trend"]}[int(label.split()[1])]
    return {"n": [], "c": ["const"], "ct": ["const", "trend"]}[label.split()[0]]


def form_of(test_name, det):
    """The case label of the remaining deterministic terms in the test's family (or a plain description)."""
    det = [d for d in ("const", "trend") if d in det]
    if det == ["trend"]:
        return "trend only (no matching case)"
    fam = family(test_name)
    if fam == "EG":
        return {0: "n", 1: "c", 2: "ct"}[len(det)]
    if fam == "Johansen":
        return f"det_order {len(det) - 1}"
    if not det:
        return "case 1"
    if det == ["const"]:
        case = ardl_case(test_name)
        return f"case {case if case in (2, 3) else 3}"
    return f"case {ardl_case(test_name)}"


def tested_row(test_name, trend_type, term, lambda_split=False):
    """Name of the estimate row whose p-value decides `term` (module docstring)."""
    if lambda_split or family(test_name) in ("EG", "Johansen"):
        return f"LR: {term}"
    return f"LR: {term}" if (ardl_case(test_name), term) in ((2, "const"), (4, "trend")) else term


class Screen:
    """The (bank, test_name, IC/selected lag, trend type) specs that passed the screen (read only)."""

    def __init__(self, screen=None):
        s = screen if isinstance(screen, pd.DataFrame) else pd.read_csv(screen or HERE / SCREEN_NAME)
        self.passed = set(map(tuple, s[SPEC].drop_duplicates().to_numpy()))


def prune(keys, det, refit, pvalue_of, alpha=ALPHA, asymmetric=False):
    """Run the rule on one model; the model is always kept.

    keys        (bank, test_name, IC/selected lag, trend type), unchanged by pruning
    det         deterministic terms of the qualifying case
    refit(det) -> fitted model with those deterministic terms
    pvalue_of(model, term) -> (p, tested_on row name)
    Returns (model, remaining det, log rows).
    """
    det = [d for d in ("const", "trend") if d in det]
    qualifying = case_of(keys[1], keys[3])
    model, log = refit(det), []
    while True:
        dropped = None
        for term in (t for t in ORDER if t in det):
            p, row = pvalue_of(model, term)
            entry = dict(zip(SPEC, keys), asymmetric=asymmetric, term=term, p_value=p, tested_on=row,
                         qualifying_case=qualifying)
            if p >= alpha:
                det = [d for d in det if d != term]
                model, dropped = refit(det), term
                log.append({**entry, "action": f"dropped {term}; refit"})
                break
            log.append({**entry, "action": "kept (significant)"})
        if dropped is None:
            break
        # a refit can change the other term's p-value: test everything that remains again
        log = [r for r in log if r["action"] != "kept (significant)"]
    form = form_of(keys[1], det)
    differs = det != det_of(keys[3])
    for r in log:
        r["remaining_form"], r["form_differs_from_qualifying_test"] = form, differs
    return model, det, log


def write_log(path, rows, asymmetric):
    """Replace this script's half (symmetric or asymmetric) of the pruning log, keep the other."""
    path = Path(path)
    new = pd.DataFrame(rows, columns=LOG_COLUMNS)
    if path.exists():
        old = pd.read_csv(path)
        if list(old.columns) == LOG_COLUMNS:
            old = old[old["asymmetric"].astype(bool) != asymmetric]
            new = pd.concat([old, new], ignore_index=True) if len(old) else new
    new = new.sort_values("asymmetric", kind="stable")
    new.to_csv(path, index=False)
    return new


# Dry run -------------------------------------------------------------------------------------
def dry_run(estimates, alpha=ALPHA):
    """From an estimation CSV: models with a deterministic term at p >= alpha (pre-refit p-values;
    only the first drop is exact, later p-values change on refit)."""
    out = []
    for keys, g in pd.read_csv(estimates).groupby(SPEC, sort=False):
        p = dict(zip(g["term"], g["p_value"]))
        split = "ect_pos.L1" in p
        det = [d for d in ("const", "trend") if d in p or f"LR: {d}" in p]
        ps = {t: p.get(tested_row(keys[1], keys[3], t, split), float("nan")) for t in ORDER if t in det}
        first = next((t for t in ORDER if t in ps and ps[t] >= alpha), None)
        if first is None:
            continue
        out.append({"bank": keys[0].split()[0], "test": base_test_name(keys[1]).replace("ARDL bounds F ", "")
                    .replace("Johansen VECM (rank 1)", "Johansen"), "asym": keys[1].endswith(ASYM_TAG),
                    "IC": keys[2].split(" / ")[0], "case": case_of(keys[1], keys[3]),
                    "p_trend": round(ps["trend"], 3) if "trend" in ps else "",
                    "p_const": round(ps["const"], 3) if "const" in ps else "", "first_drop": first})
    return pd.DataFrame(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dry run of the deterministic-term pruning (no fitting).")
    ap.add_argument("--estimates", default=HERE / "ECM estimation results.csv")
    ap.add_argument("--asym-estimates", default=HERE / "ECM asymmetric estimation results.csv")
    ap.add_argument("--alpha", type=float, default=ALPHA)
    args = ap.parse_args(argv)
    pd.set_option("display.width", 200)
    for path in (args.estimates, args.asym_estimates):
        t = dry_run(path, args.alpha)
        print(f"\n{Path(path).name}: {len(t)} model(s) with a deterministic term at p >= {args.alpha}")
        if len(t):
            print(t.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

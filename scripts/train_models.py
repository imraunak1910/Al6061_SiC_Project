"""Phase 4: paper-level validation + model training.  Run: python scripts/train_models.py

Validation = leave-one-paper-out (LOPO). Rows from one paper are never split between train and test.
A target is "eligible" for the app only if it has >= MIN_PAPERS papers, >= MIN_OBS observations
AND the best LOPO model beats the mean-of-training baseline on MAE.
"""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
MIN_PAPERS, MIN_OBS = 3, 10
FEATURES = ["SiC_wt_pct"]  # the only feature compatibly reported by every core paper (see README)
TARGETS = ["UTS_MPa", "Yield_strength_MPa", "Vickers_HV", "Elongation_pct"]
MODELS = {
    "Baseline (mean)": DummyRegressor(strategy="mean"),
    "Linear Regression": LinearRegression(),
    "Random Forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=1, random_state=0),
    "Extra Trees": ExtraTreesRegressor(n_estimators=300, random_state=0),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, max_depth=2, learning_rate=0.1, random_state=0),
}

df = pd.read_csv(ROOT / "data/Al6061_SiC_Master_Dataset_v5.csv")
sets = {
    "primary_core": df[(df.Category == "A") & (df.Model_Set == "Primary")],
    # diagnostic: add supplementary as-cast rows (not heat treated, not calculated, not T6-flagged N28)
    "sensitivity_plus_supplementary": df[((df.Category == "A") & (df.Model_Set == "Primary"))
                                         | ((df.Model_Set == "Sensitivity") & (df.HT_class == "As-cast"))],
}


def lopo(d, prop, model):
    d = d[d.Property == prop].dropna(subset=FEATURES + ["Value"])
    papers = d.Paper_ID.unique()
    if len(papers) < 2:
        return None
    pred = pd.Series(index=d.index, dtype=float); folds = []
    for p in papers:
        te = d.Paper_ID == p
        m = clone(model).fit(d.loc[~te, FEATURES], d.loc[~te, "Value"])
        pred[te] = m.predict(d.loc[te, FEATURES])
        folds.append(dict(paper=p, n=int(te.sum()), mae=float(mean_absolute_error(d.loc[te, "Value"], pred[te]))))
    y = d.Value
    return dict(MAE=mean_absolute_error(y, pred), RMSE=mean_squared_error(y, pred) ** .5, R2=r2_score(y, pred), folds=folds)


rows, cards = [], {}
for sname, d in sets.items():
    for prop in TARGETS:
        dd = d[d.Property == prop]
        npap, nobs = dd.Paper_ID.nunique(), len(dd)
        res = {}
        for mname, m in MODELS.items():
            r = lopo(d, prop, m)
            if r is None:
                rows.append(dict(Set=sname, Target=prop, Model=mname, N_papers=npap, N_obs=nobs, MAE=np.nan, RMSE=np.nan, R2=np.nan,
                                 Note="Only 1 paper: paper-level validation impossible"))
                continue
            res[mname] = r
            rows.append(dict(Set=sname, Target=prop, Model=mname, N_papers=npap, N_obs=nobs, MAE=r["MAE"], RMSE=r["RMSE"], R2=r["R2"],
                             Note="LOPO, pooled held-out predictions"))
        if sname != "primary_core":
            continue
        card = dict(target=prop, n_papers=npap, n_obs=nobs, papers=sorted(dd.Paper_ID.unique()),
                    sic_min=float(dd.SiC_wt_pct.min()) if nobs else None, sic_max=float(dd.SiC_wt_pct.max()) if nobs else None,
                    features=FEATURES, eligible=False, reason="", best_model=None, metrics=None)
        if npap < MIN_PAPERS or nobs < MIN_OBS:
            card["reason"] = f"Only {npap} independent paper(s) / {nobs} observations (need >= {MIN_PAPERS} papers and >= {MIN_OBS} obs)."
        else:
            base = res["Baseline (mean)"]["MAE"]
            cand = {k: v for k, v in res.items() if k != "Baseline (mean)"}
            best = min(cand, key=lambda k: cand[k]["MAE"])
            card["metrics"] = {k: {x: float(v[x]) for x in ("MAE", "RMSE", "R2")} for k, v in res.items()}
            if cand[best]["MAE"] < base:
                card.update(eligible=True, best_model=best, reason=f"{best} LOPO MAE {cand[best]['MAE']:.2f} < baseline {base:.2f}.")
            else:
                card["reason"] = f"No model beats the mean baseline under leave-one-paper-out (best {best}: {cand[best]['MAE']:.2f} vs baseline {base:.2f})."
        # always save a diagnostic model so the work is reproducible; only eligible ones are used by the app
        mname = card["best_model"] or "Linear Regression"
        X, y = dd[FEATURES], dd.Value
        if nobs:
            joblib.dump(clone(MODELS[mname]).fit(X, y), ROOT / f"models/{prop}__{mname.replace(' ', '_')}.joblib")
            card["saved_model"] = f"models/{prop}__{mname.replace(' ', '_')}.joblib"
        cards[prop] = card

out = pd.DataFrame(rows)
out.to_csv(ROOT / "reports/model_validation.csv", index=False)
json.dump(cards, open(ROOT / "models/model_cards.json", "w"), indent=2)
pd.set_option("display.width", 200)
print(out.round(2).to_string())
for k, v in cards.items():
    print(k, "ELIGIBLE" if v["eligible"] else "NOT eligible", "-", v["reason"])

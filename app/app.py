"""Al6061-SiC Mechanical Property Predictor (academic prototype).  Run: streamlit run app/app.py"""
import json
from pathlib import Path
import zipfile
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PAPER_ARCHIVE = ROOT / "Al6061_SiC_Organized_20_Papers.zip"
INSUFFICIENT = "Insufficient verified experimental data to provide a reliable prediction."
LABELS = {"UTS_MPa": ("Ultimate tensile strength", "MPa"), "Yield_strength_MPa": ("Yield strength", "MPa"),
          "Vickers_HV": ("Hardness (Vickers)", "HV"), "Elongation_pct": ("Elongation", "%")}

st.set_page_config(page_title="Al6061–SiC Property Predictor", layout="wide")


@st.cache_data
def load():
    df = pd.read_csv(ROOT / "data/Al6061_SiC_Master_Dataset_v5.csv")
    cards = json.load(open(ROOT / "models/model_cards.json"))
    val = pd.read_csv(ROOT / "reports/model_validation.csv")
    papers = pd.read_csv(ROOT / "data/Paper_Index_v5.csv")
    with zipfile.ZipFile(PAPER_ARCHIVE) as archive:
        with archive.open("Al6061_SiC_Paper_File_Mapping.csv") as mapping_file:
            paper_mapping = pd.read_csv(mapping_file)
    pdfs = paper_mapping.set_index("Paper_ID")["Renamed_filename"].to_dict()
    return df, cards, val, papers, pdfs


df, cards, val, papers, pdfs = load()
core = df[(df.Category == "A") & (df.Model_Set == "Primary")]

st.title("Al6061–SiC Mechanical Property Predictor")
st.warning("Academic prototype. Outputs are literature-based estimates, **not** certified engineering design values. "
           "The training set is very small (2–3 independent papers per property); read Section 6 before using any number.")

# ------------------------------------------------------------------ 1. inputs
st.header("1. Material and process inputs")
c1, c2 = st.columns([1, 1])
with c1:
    sic = st.slider("SiC concentration (wt.%)", 0.0, 25.0, 5.0, 0.5,
                    help="The only input the trained models use. Core training data cover 0–15 wt.%.")
    st.caption("Model inputs used: **SiC wt.% only**.")
with c2:
    st.info("**Not model inputs:** particle size, manufacturing process, stirring speed, melt temperature, SiC preheat, "
            "heat treatment and aging. The compatible core papers either do not report them or do not vary them, so "
            "controls for them would be cosmetic. They are shown below only as *literature-lookup filters*.")
    fam = st.multiselect("Literature lookup: process family (does NOT change the prediction)",
                         sorted(df.Process_family.dropna().unique()), default=["Casting (stir)"])
    htc = st.multiselect("Literature lookup: heat-treatment state (does NOT change the prediction)",
                         sorted(df.HT_class.dropna().unique()), default=["As-cast"])

# ------------------------------------------------------------------ 2. predictions
st.header("2. Literature-based property values (no machine learning)")
st.markdown("Each row is what **one paper actually measured** at this composition: an exact reported value, or a straight-line "
            "interpolation between that paper's two nearest measured compositions. Nothing is extrapolated and nothing is averaged "
            "into a fake single answer. Pick the source whose process matches yours.")
cA, cB = st.columns(2)
inc_bad = cA.checkbox("Include implausible N02 values (UTS 39–56 MPa)", False)
max_gap = st.slider("Maximum gap to interpolate across (wt.%)", 1.0, 10.0, 5.0, 0.5,
                    help="A paper is only interpolated if its two neighbouring measured compositions are at most this far apart.")
inc_derived = cB.checkbox("Include values calculated from reported % improvements (N07)", False)
LIT_PROPS = {**LABELS, "Brinell_HB": ("Hardness (Brinell) — separate scale", "HB")}
lit = df[df.Category.isin(["A", "B"]) & df.Property.isin(list(LIT_PROPS)) & df.Process_family.isin(fam) & df.HT_class.isin(htc)
         & (df.Model_Set != "Aging-only")].copy()
if not inc_derived:
    lit = lit[lit.Value_type != "calculated"]
if not inc_bad:
    lit = lit[lit.Use_group != "Sensitivity_review_implausible"]


def lookup(g, x):
    g = g.groupby("SiC_wt_pct", as_index=False).Value.mean().sort_values("SiC_wt_pct")
    xs, ys = g.SiC_wt_pct.values, g.Value.values
    hit = np.isclose(xs, x)
    if hit.any():
        return float(ys[hit][0]), f"measured at {x:g} wt.%"
    if len(xs) >= 2 and xs[0] < x < xs[-1]:
        i = np.searchsorted(xs, x)
        if xs[i] - xs[i - 1] > max_gap:
            return None, f"gap too wide ({xs[i-1]:g}–{xs[i]:g} wt.% has no data)"
        return float(np.interp(x, xs, ys)), f"interpolated between {xs[i-1]:g} and {xs[i]:g} wt.%"
    return None, f"outside this paper's range ({xs[0]:g}–{xs[-1]:g} wt.%)"


@st.cache_data
def load_pdf(filename):
    with zipfile.ZipFile(PAPER_ARCHIVE) as archive:
        return archive.read(f"papers_renamed/{filename}")


def show_pdf_downloads(paper_ids, context):
    available_ids = [paper_id for paper_id in dict.fromkeys(paper_ids) if paper_id in pdfs]
    if available_ids:
        pdf_columns = st.columns(min(len(available_ids), 4))
        for index, paper_id in enumerate(available_ids):
            with pdf_columns[index % len(pdf_columns)]:
                st.download_button(
                    f"Download {paper_id} PDF",
                    data=load_pdf(pdfs[paper_id]),
                    file_name=pdfs[paper_id],
                    mime="application/pdf",
                    key=f"paper-pdf-{context}-{paper_id}",
                )
        st.caption("PDFs are loaded locally from the ZIP archive; download a button above to open the paper.")


lit_tabs = st.columns(2)
for k, (prop, (name, unit)) in enumerate(LIT_PROPS.items()):
    rows = []
    for (pid, ht), g in lit[lit.Property == prop].groupby(["Paper_ID", "HT_class"]):
        v, how = lookup(g, sic)
        if v is None:
            continue
        flag = "⚠ credibility flag" if "credibility" in g.Use_group.iloc[0] else ("single point" if g.SiC_wt_pct.nunique() == 1 else "")
        rows.append({"Source": pid, "Paper": g.Citation.iloc[0][:70], "Value": round(v, 2), "How obtained": how,
                     "Where in paper": g.Source_location.iloc[0],
                     "Local PDF": "Available" if pid in pdfs else "Not in archive",
                     "Heat treatment": ht, "Particle size": g.Particle_size_note.iloc[0], "Note": flag})
    with lit_tabs[k % 2]:
        st.subheader(f"{name} ({unit})")
        if not rows:
            st.warning(f"No paper measured {name} at {sic:g} wt.% (or close enough to interpolate). "
                       "Nearest measured points are shown instead; they are NOT values at your composition.")
            near = []
            for (pid, ht), g in lit[lit.Property == prop].groupby(["Paper_ID", "HT_class"]):
                j = (g.SiC_wt_pct - sic).abs().idxmin()
                near.append({"Source": pid, "Nearest measured (wt.% SiC)": g.loc[j, "SiC_wt_pct"],
                             "Distance (wt.%)": round(abs(g.loc[j, "SiC_wt_pct"] - sic), 2), "Value": g.loc[j, "Value"],
                             "Paper": g.Citation.iloc[0][:70], "Where in paper": g.loc[j, "Source_location"],
                             "Local PDF": "Available" if pid in pdfs else "Not in archive", "Heat treatment": ht})
            if near:
                near_df = pd.DataFrame(near).sort_values("Distance (wt.%)")
                st.dataframe(near_df, width="stretch", hide_index=True)
                show_pdf_downloads(near_df["Source"].tolist(), f"{prop}-nearest")
            else:
                st.info("No data for this property under the current filters.")
            continue
        t = pd.DataFrame(rows)
        lo, hi, med = t.Value.min(), t.Value.max(), t.Value.median()
        st.write(f"**{len(t)} source(s)**: {lo:.1f} – {hi:.1f} {unit} (median {med:.1f})")
        if len(t) > 1 and hi / max(lo, 1e-9) > 1.25:
            st.caption("Sources disagree substantially, because process, particle size and test setup differ. Use the matching source, not the median.")
        st.dataframe(t, width="stretch", hide_index=True)
        show_pdf_downloads(t["Source"].tolist(), prop)

st.divider()
st.header("2b. Machine-learning estimate (experimental; only hardness is validated)")
explore = st.checkbox("Show exploratory estimates for the disabled properties (NOT validated)", value=True,
                      help="Simple linear trend on SiC wt.% fitted to all core rows. Shown so every property can be seen; "
                           "its validation error is displayed beside it and is usually worse than just quoting the average.")
cols = st.columns(4)
window = st.sidebar.slider("Nearby-literature window (± wt.%)", 0.5, 5.0, 1.5, 0.5)
for col, prop in zip(cols, LABELS):
    name, unit = LABELS[prop]
    card = cards[prop]
    with col:
        st.subheader(name)
        if not card["eligible"]:
            st.error(INSUFFICIENT)
            st.caption(card["reason"])
            if explore and card.get("saved_model"):
                if not (card["sic_min"] <= sic <= card["sic_max"]):
                    st.caption(f"Exploratory estimate not shown: outside {card['sic_min']:g}–{card['sic_max']:g} wt.%.")
                else:
                    m = joblib.load(ROOT / card["saved_model"])
                    ex = float(m.predict(pd.DataFrame({"SiC_wt_pct": [sic]}))[0])
                    st.metric(f"Exploratory ({unit}) — NOT validated", f"{ex:.1f}")
                    v = val[(val.Set == "primary_core") & (val.Target == prop)].set_index("Model").MAE
                    if v.notna().any():
                        st.caption(f"Linear trend, leave-one-paper-out MAE {v['Linear Regression']:.1f} {unit}; "
                                   f"simply quoting the training mean would give {v['Baseline (mean)']:.1f} {unit}. "
                                   "Treat as a rough trend line only.")
                    else:
                        st.caption("Fitted to a single paper; cannot be validated at all.")
        elif not (card["sic_min"] <= sic <= card["sic_max"]):
            st.warning(f"{sic:g} wt.% is outside the training range ({card['sic_min']:g}–{card['sic_max']:g} wt.%). "
                       "No confident prediction is shown.")
        else:
            model = joblib.load(ROOT / card["saved_model"])
            pred = float(model.predict(pd.DataFrame({"SiC_wt_pct": [sic]}))[0])
            mae = card["metrics"][card["best_model"]]["MAE"]
            st.metric(f"Predicted ({unit})", f"{pred:.1f}", help=f"Model: {card['best_model']}")
            st.caption(f"Typical paper-level error ≈ ±{mae:.0f} {unit} (leave-one-paper-out MAE). "
                       f"Model: {card['best_model']}. Trained on {card['n_obs']} observations from {card['n_papers']} papers.")
            st.caption("⚠ Fragile: adding supplementary data removes the skill (see Section 3).")

st.subheader("Experimental values reported near this composition (lookup, not prediction)")
f = df[df.Category.isin(["A", "B"]) & df.Property.isin(list(LABELS) + ["Brinell_HB"])
       & (df.Value_type != "calculated") & df.Process_family.isin(fam) & df.HT_class.isin(htc)
       & (df.SiC_wt_pct.sub(sic).abs() <= window)]
if f.empty:
    st.write("No literature observations match these filters.")
else:
    st.dataframe(f[["Paper_ID", "Citation", "SiC_wt_pct", "SiC_wt_basis", "Property", "Value", "Unit", "Category", "Data_status", "Quality_note"]]
                 .sort_values(["Property", "SiC_wt_pct"]), width="stretch", hide_index=True)
    st.caption("Different papers use different processes and test conditions; values are not directly comparable. "
               "Category B and flagged rows are not used for training.")

# ------------------------------------------------------------------ 3. performance
st.header("3. Model performance")
st.markdown("Validation is **leave-one-paper-out**: a paper is never split between training and testing. "
            "Metrics are pooled over held-out papers. A target is enabled only if it has ≥3 independent papers, ≥10 observations, "
            "and a model that beats the mean baseline.")
p = val[val.Set == "primary_core"].copy()
p["Target"] = p.Target.map(lambda t: LABELS[t][0])
st.dataframe(p[["Target", "Model", "N_papers", "N_obs", "MAE", "RMSE", "R2", "Note"]].round(2), width="stretch", hide_index=True)
for prop, c in cards.items():
    st.write(f"**{LABELS[prop][0]}** — {'enabled' if c['eligible'] else 'disabled'}: {c['reason']}")
with st.expander("Sensitivity check: add supplementary as-cast rows (diagnostic only)"):
    s = val[val.Set == "sensitivity_plus_supplementary"].copy()
    s["Target"] = s.Target.map(lambda t: LABELS[t][0])
    st.dataframe(s[["Target", "Model", "N_papers", "N_obs", "MAE", "RMSE", "R2"]].round(2), width="stretch", hide_index=True)
    st.caption("Hardness skill disappears (R² < 0) once more papers/processes are added — the core result is not robust.")

# ------------------------------------------------------------------ 4. visualisation
st.header("4. Experimental data visualisation")
prop = st.selectbox("Property", list(LABELS), format_func=lambda k: LABELS[k][0])
show_supp = st.checkbox("Include supplementary / flagged binary data (hollow markers)", True)
fig, ax = plt.subplots(figsize=(8, 4.5))
marks = "osD^vPX*"
base = df[df.Category.isin(["A", "B"]) & (df.Property == prop) & (df.Value_type != "calculated") & df.HT_class.isin(["As-cast", "Unknown (before/after HT not specified)"])]
for i, (pid, g) in enumerate(base.groupby("Paper_ID")):
    isc = (g.Category == "A") & (g.Model_Set == "Primary")
    if isc.any():
        ax.scatter(g.SiC_wt_pct[isc], g.Value[isc], marker=marks[i % len(marks)], s=55, color=f"C{i % 10}", label=f"{pid} (core)")
    if show_supp and (~isc).any():
        ax.scatter(g.SiC_wt_pct[~isc], g.Value[~isc], marker=marks[i % len(marks)], s=55, facecolors="none", edgecolors=f"C{i % 10}", label=f"{pid} (suppl.)")
if cards[prop]["eligible"]:
    xs = np.linspace(cards[prop]["sic_min"], cards[prop]["sic_max"], 50)
    ax.plot(xs, joblib.load(ROOT / cards[prop]["saved_model"]).predict(pd.DataFrame({"SiC_wt_pct": xs})), "k--", label="model (eligible)")
ax.axvline(sic, color="grey", lw=.8, ls=":")
ax.set_xlabel("SiC (wt.%)"); ax.set_ylabel(f"{LABELS[prop][0]} ({LABELS[prop][1]})"); ax.grid(alpha=.3); ax.legend(fontsize=7, ncol=2)
st.pyplot(fig)
st.caption("As-cast binary data only. Brinell and Rockwell values are never plotted with Vickers. Heat-treated data are in the workbook "
           "(aging series, 15 vol.% SiC, one paper) but are not used.")

# ------------------------------------------------------------------ 5. papers
st.header("5. Supporting research papers")
used = core.Paper_ID.unique()
pp = papers[papers.Paper_ID.isin(used)].copy()
pp["Local PDF"] = pp.Paper_ID.map(lambda pid: "Available" if pid in pdfs else "Not in archive")
st.markdown("**Papers contributing training data**")
st.dataframe(pp[["Paper_ID", "Citation", "Disposition", "Rows", "Local PDF"]], width="stretch", hide_index=True)
with st.expander("All papers screened (including candidates not yet extracted)"):
    pa = papers.copy()
    pa["Local PDF"] = pa.Paper_ID.map(lambda pid: "Available" if pid in pdfs else "Not in archive")
    st.dataframe(pa[["Paper_ID", "Citation", "Disposition", "Reason", "Local PDF"]], width="stretch", hide_index=True)

# ------------------------------------------------------------------ 6. limitations
st.header("6. Prediction reliability and limitations")
st.markdown("""
- **Tiny, heterogeneous data.** Core training data: UTS 2 papers, yield 1, elongation 2, Vickers hardness 3. Papers differ in particle size, melt practice and test setup, and even their unreinforced controls differ (UTS 103–126 MPa; HV 68–96).
- **Single feature.** Only SiC wt.% is modelled. Process and heat treatment are *not* inputs.
- **Non-monotonic behaviour.** The 14–15 wt.% points of the highest-SiC paper show *falling* strength (clustering/porosity), which a simple trend cannot capture.
- **Not verified against PDFs** for rows added in v5; earlier rows carried over from v1–v4.
- **Excluded or separate:** hybrids, welding, powder-metallurgy, simulation, vol.%-only studies, hardness on other scales and values derived from percentages.
- Outside 0–15 wt.% the app declines to predict.
""")

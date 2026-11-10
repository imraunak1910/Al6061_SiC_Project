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

st.title("Al6061–SiC Property Explorer")
st.caption("Explore reported results by SiC content. Values are from individual papers and are not design recommendations.")

with st.sidebar:
    st.subheader("Choose material")
    sic = st.slider("SiC content (wt.%)", 0.0, 25.0, 5.0, 0.5)
    process_options = ["All processes"] + sorted(df.Process_family.dropna().unique())
    process = st.selectbox("Process", process_options, index=process_options.index("Casting (stir)") if "Casting (stir)" in process_options else 0)
    treatment_options = ["As-cast", "All treatments"] + sorted(
        option for option in df.HT_class.dropna().unique() if option != "As-cast"
    )
    treatment = st.selectbox("Heat treatment", treatment_options)
    with st.expander("More filters"):
        max_gap = st.slider("Largest gap to fill (wt.%)", 1.0, 10.0, 5.0, 0.5)
        inc_derived = st.checkbox("Include calculated values", False)
        inc_bad = st.checkbox("Include flagged UTS values", False)

LIT_PROPS = {**LABELS, "Brinell_HB": ("Brinell hardness", "HB")}
lit = df[df.Category.isin(["A", "B"]) & df.Property.isin(list(LIT_PROPS))
         & (df.Model_Set != "Aging-only")].copy()
if process != "All processes":
    lit = lit[lit.Process_family == process]
if treatment != "All treatments":
    lit = lit[lit.HT_class == treatment]
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
                    f"PDF · {paper_id}",
                    data=load_pdf(pdfs[paper_id]),
                    file_name=pdfs[paper_id],
                    mime="application/pdf",
                    key=f"paper-pdf-{context}-{paper_id}",
                )
        st.caption("Downloads from the local paper archive.")


tabs = st.tabs(["Reported values", "Estimate", "Charts", "Papers"])
with tabs[0]:
    st.subheader(f"Results near {sic:g} wt.% SiC")
    st.caption("Each result is shown separately by source. Values may be measured or interpolated within that paper's data.")
    prop_tabs = st.tabs([name for name, _ in LABELS.values()])
    for (prop, (name, unit)), tab in zip(LABELS.items(), prop_tabs):
        with tab:
            results = []
            nearest = []
            for (pid, condition), group in lit[lit.Property == prop].groupby(["Paper_ID", "HT_class"]):
                value, how = lookup(group, sic)
                nearest_index = (group.SiC_wt_pct - sic).abs().idxmin()
                nearest_row = group.loc[nearest_index]
                if value is not None:
                    results.append({
                        "Paper": group.Citation.iloc[0],
                        "Value": f"{value:.2f} {unit}",
                        "At": f"{how}",
                        "Condition": condition,
                        "Source": pid,
                    })
                nearest.append({
                    "Paper": group.Citation.iloc[0],
                    "Value": f"{nearest_row.Value:g} {unit}",
                    "Measured at": f"{nearest_row.SiC_wt_pct:g} wt.%",
                    "Distance": abs(nearest_row.SiC_wt_pct - sic),
                    "Condition": condition,
                    "Source": pid,
                })
            if results:
                result_table = pd.DataFrame(results)
                st.dataframe(result_table[["Paper", "Value", "At", "Condition"]], width="stretch", hide_index=True)
                show_pdf_downloads(result_table["Source"].tolist(), f"{prop}-results")
            elif nearest:
                st.info(f"No value available at {sic:g} wt.% for this property. Nearest reported measurements:")
                nearest_table = pd.DataFrame(nearest).sort_values("Distance").head(5)
                st.dataframe(nearest_table[["Paper", "Value", "Measured at", "Condition"]], width="stretch", hide_index=True)
                show_pdf_downloads(nearest_table["Source"].tolist(), f"{prop}-nearest")
            else:
                st.info("No papers match the selected filters.")
    with st.expander("Brinell hardness (different scale)"):
        brinell = lit[lit.Property == "Brinell_HB"]
        rows = []
        for (pid, condition), group in brinell.groupby(["Paper_ID", "HT_class"]):
            value, how = lookup(group, sic)
            if value is not None:
                rows.append({
                    "Paper": group.Citation.iloc[0],
                    "Value": f"{value:.2f} HB",
                    "At": how,
                    "Condition": condition,
                    "Source": pid,
                })
        if rows:
            brinell_table = pd.DataFrame(rows)
            st.dataframe(brinell_table[["Paper", "Value", "At", "Condition"]], width="stretch", hide_index=True)
            show_pdf_downloads(brinell_table["Source"].tolist(), "brinell-results")
        else:
            st.write("No Brinell measurements match the selected filters.")

with tabs[1]:
    st.subheader("Hardness estimate")
    card = cards["Vickers_HV"]
    if card["eligible"] and card["sic_min"] <= sic <= card["sic_max"]:
        model = joblib.load(ROOT / card["saved_model"])
        prediction = float(model.predict(pd.DataFrame({"SiC_wt_pct": [sic]}))[0])
        st.metric("Estimated Vickers hardness", f"{prediction:.1f} HV")
        st.caption("Experimental estimate from a small dataset. Not a design value.")
        with st.expander("How reliable is this estimate?"):
            st.write(
                f"Tested on {card['n_papers']} papers ({card['n_obs']} observations). "
                f"Average error when testing on unseen papers: about "
                f"{card['metrics'][card['best_model']]['MAE']:.1f} HV. "
                "The result is sensitive to which papers are included."
            )
    else:
        st.info("No reliable estimate is available for this composition.")
    st.caption("Strength and elongation estimates are hidden because there are not enough independent studies.")
    with st.expander("Model results"):
        primary = val[val.Set == "primary_core"].copy()
        primary["Property"] = primary.Target.map(lambda target: LABELS[target][0])
        primary = primary[primary.Model.isin(["Baseline (mean)", "Linear Regression"])]
        st.dataframe(
            primary[["Property", "Model", "N_papers", "N_obs", "MAE", "R2"]].round(2),
            width="stretch",
            hide_index=True,
        )
        st.caption("Testing holds out a whole paper at a time. Adding supplementary data removes the apparent hardness-model skill.")

# ------------------------------------------------------------------ 4. visualisation
with tabs[2]:
    st.subheader("Property vs SiC content")
    chart_property = st.selectbox("Property", list(LABELS), format_func=lambda key: LABELS[key][0])
    show_supplementary = st.checkbox("Show supplementary data", False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    markers = "osD^vPX*"
    chart_data = df[
        df.Category.isin(["A", "B"])
        & (df.Property == chart_property)
        & (df.Value_type != "calculated")
        & df.HT_class.isin(["As-cast", "Unknown (before/after HT not specified)"])
    ]
    for index, (paper_id, group) in enumerate(chart_data.groupby("Paper_ID")):
        is_primary = (group.Category == "A") & (group.Model_Set == "Primary")
        color = f"C{index % 10}"
        if is_primary.any():
            ax.scatter(
                group.SiC_wt_pct[is_primary], group.Value[is_primary],
                marker=markers[index % len(markers)], color=color, s=48, label=paper_id,
            )
        if show_supplementary and (~is_primary).any():
            ax.scatter(
                group.SiC_wt_pct[~is_primary], group.Value[~is_primary],
                marker=markers[index % len(markers)], facecolors="none",
                edgecolors=color, s=48, label=f"{paper_id} (other)",
            )
    ax.axvline(sic, color="grey", linewidth=.8, linestyle=":")
    ax.set_xlabel("SiC (wt.%)")
    ax.set_ylabel(f"{LABELS[chart_property][0]} ({LABELS[chart_property][1]})")
    ax.grid(alpha=.25)
    ax.legend(fontsize=8, ncol=2)
    st.pyplot(fig)

with tabs[3]:
    st.subheader("Papers")
    local_paper_ids = [paper_id for paper_id in pdfs if paper_id in papers.Paper_ID.values]
    if local_paper_ids:
        citation_by_id = papers.set_index("Paper_ID")["Citation"].to_dict()
        selected_paper = st.selectbox(
            "Choose a local paper",
            local_paper_ids,
            format_func=lambda paper_id: f"{paper_id} — {citation_by_id[paper_id]}",
        )
        show_pdf_downloads([selected_paper], "paper-library")
    core_papers = papers[papers.Paper_ID.isin(core.Paper_ID.unique())].copy()
    core_papers["PDF"] = core_papers.Paper_ID.map(lambda paper_id: "Available" if paper_id in pdfs else "Not available")
    st.dataframe(
        core_papers[["Paper_ID", "Citation", "Disposition", "PDF"]],
        width="stretch",
        hide_index=True,
    )
    with st.expander("All screened papers"):
        all_papers = papers.copy()
        all_papers["PDF"] = all_papers.Paper_ID.map(lambda paper_id: "Available" if paper_id in pdfs else "Not available")
        st.dataframe(
            all_papers[["Paper_ID", "Citation", "Disposition", "PDF"]],
            width="stretch",
            hide_index=True,
        )
    with st.expander("About this tool"):
        st.write(
            "This is a literature-based academic prototype. Some source values have not been checked "
            "against the original PDF. Results are not certified material properties or design values."
        )

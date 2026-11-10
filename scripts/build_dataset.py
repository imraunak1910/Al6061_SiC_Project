"""Build the v5 master workbook + CSVs from the v4 audit workbook and new_records_v5.

Run:  python scripts/build_dataset.py
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from new_records_v5 import NEW_PAPERS, new_rows  # noqa: E402

SRC = ROOT / "data/source/Al6061_SiC_MultiPaper_Audit_v4.xlsx"
OUT_X = ROOT / "data/Al6061_SiC_Master_Dataset_v5.xlsx"
OUT_ALL = ROOT / "data/Al6061_SiC_Master_Dataset_v5.csv"
OUT_CORE = ROOT / "data/Al6061_SiC_Core_Training_v5.csv"

RHO_AL, RHO_SIC = 2.70, 3.21  # g/cm3 assumptions for vol% -> wt% (declared, flagged as derived)


def vol_to_wt(v):
    return 100 * v * RHO_SIC / (v * RHO_SIC + (100 - v) * RHO_AL)


PROP_MAP = {"Vickers hardness": "Vickers_HV", "Compressive strength": "Compressive_strength_MPa"}
# per-paper process metadata for rows inherited from v4 (only what the v4 workbook states)
OLD_META = {
    "P01": dict(psize=None, psize_note="not in v4 workbook - extract from PDF", melt=None, rpm=None, preheat=None),
    "N01": dict(psize=44, psize_note="44 um", melt=750, rpm=650, preheat=350),
    "P04": dict(psize=None, psize_note="not in v4 workbook", melt=None, rpm=None, preheat=None),
    "N02": dict(psize=None, psize_note="not in v4 workbook", melt=None, rpm=None, preheat=None),
    "N03": dict(psize=None, psize_note="not in v4 workbook", melt=None, rpm=None, preheat=None),
    "N07": dict(psize=23, psize_note="23 um; melt 740-760 C (midpoint stored); 1% Mg", melt=750, rpm=350, preheat=600),
    "N08": dict(psize=None, psize_note="not in abstract", melt=None, rpm=None, preheat=None),
    "N17": dict(psize=None, psize_note="not in v4 workbook", melt=None, rpm=None, preheat=None),
}
OLD_CLASS = {  # Category, Use_group, Model_Set
    "P01": ("A", "Core_candidate", "Primary"), "N01": ("A", "Core_candidate", "Primary"),
    "P04": ("B", "Supplementary_binary", "No"),   # compression / hardness controls; process info missing
    "N02": ("B", "Sensitivity_review_implausible", "Sensitivity"),
    "N03": ("B", "Supplementary_single_point", "No"),
    "N08": ("B", "Supplementary_single_point", "Sensitivity"),
    "N07": ("B", "Supplementary_exact", "Sensitivity"),
    "N17": ("C", "Hybrid", "No"),
}
V_OLD = "Extracted from PDF/abstract in earlier sessions (v1-v4); carried over unchanged, not re-verified here"

FULLTEXT = {  # direct full-text / open-access pages that were read in this project (else DOI link is used)
 "N24": "https://scispace.com/pdf/t4-and-t6-treatment-of-6061-al-15-vol-sicp-composite-3a3n6ayiy5.pdf",
 "N25": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5456805/",
 "N26": "https://orbi.umons.ac.be/bitstream/20.500.12907/46725/1/Characterization%20of%20the%20Al6061%20Alloy%20Reinforced%20with%20SiC%20Nanoparticles%20and%20Prepared%20via%20Powder%20Metallurgy.pdf",
 "N27": "https://academicstaff.epu.edu.iq/directory/dlair.ramadan/research/444_research_1_20230619040129398530.pdf",
 "N28": "https://ijama.in/admin/a/uploads/pdf/1779170808_IJAMAMAY26V305A13.pdf",
 "U01": "https://research.mitwpu.edu.in/pdf/publisher-pdf-fulltext-manufacture-of-silicon-carbide-reinforced",
 "U02": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6567864/",
 "U09": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11832779/",
 "N17": "https://www.frontiersin.org/journals/materials/articles/10.3389/fmats.2024.1415907/full",
}


def source_url(pid, doi):
    if pid in FULLTEXT:
        return FULLTEXT[pid]
    return f"https://doi.org/{doi}" if isinstance(doi, str) and doi.startswith("10.") else None


# ------------------------------------------------------------------ load v4
all_rec = pd.read_excel(SRC, sheet_name="All_Records")
new_v4 = pd.read_excel(SRC, sheet_name="New_Records_v4")
paper_audit = pd.read_excel(SRC, sheet_name="New_Paper_Audit")
review_src = pd.read_excel(SRC, sheet_name="Review_Sources")
n_v4_in = len(all_rec)

# ---- duplicate detection across v4 sheets
key = ["Paper_ID", "SiC_wt_pct", "Property", "Value"]
dup_rows = []
nk = new_v4.copy()
nk["SiC_wt_pct"]=nk["SiC_wt_pct"].astype(float); all_rec["SiC_wt_pct"]=all_rec["SiC_wt_pct"].astype(float); nk["Value"]=nk["Value"].astype(float); all_rec["Value"]=all_rec["Value"].astype(float)
merged = all_rec.merge(nk[key].assign(_in_new=1), on=key, how="left")
for _, r in merged[merged["_in_new"] == 1].iterrows():
    dup_rows.append(dict(Check="Same observation in All_Records and New_Records_v4", Paper_ID=r.Paper_ID,
                         SiC_wt_pct=r.SiC_wt_pct, Property=r.Property, Value=r.Value,
                         Action="Kept once (All_Records copy); New_Records_v4 copy dropped"))
internal = all_rec[all_rec.duplicated(key, keep=False)]
for _, r in internal.iterrows():
    dup_rows.append(dict(Check="Duplicate inside All_Records", Paper_ID=r.Paper_ID, SiC_wt_pct=r.SiC_wt_pct,
                         Property=r.Property, Value=r.Value, Action="Removed duplicates"))
all_rec = all_rec.drop_duplicates(key)
dup_rows.append(dict(Check="Duplicate PAPER entry", Paper_ID="N23 = N17", SiC_wt_pct=None, Property=None, Value=None,
                     Action="N23 in New_Paper_Audit is the same article as N17 (Murmu 2024); merged into N17"))

old_rows = []
for _, r in all_rec.iterrows():
    pid = r.Paper_ID
    meta = OLD_META[pid]
    cat, grp, mset = OLD_CLASS[pid]
    prop = PROP_MAP.get(r.Property, r.Property)
    status, note = r.Data_status, r.Quality_note
    if "Calculated" in str(status):
        mset = "No"
        grp = "Supplementary_derived"
    if pid == "N07":
        grp = "Supplementary_derived" if "Calculated" in str(status) else "Supplementary_exact"
    scale = {"Vickers_HV": "Vickers", "Brinell_HB": "Brinell", "Rockwell_HRH": "Rockwell H"}.get(prop)
    htc = "As-cast"
    if pid == "N03":
        htc = "Unknown (before/after HT not specified)"
    old_rows.append(dict(
        Paper_ID=pid, SiC_native=r.SiC_wt_pct, SiC_basis="wt%", Property=prop, Value=r.Value,
        Unit=("HV" if prop == "Vickers_HV" and r.Unit in ("HV/VHN", "HV10") else r.Unit),
        Hardness_scale=scale, Heat_treatment=r.Heat_treatment, HT_class=htc, Aging_T_C=None, Aging_time_h=None,
        Test_condition=str(r.Test_regime) if pd.notna(r.Test_regime) else "", Data_status=status,
        Value_type=("calculated" if "Calculated" in str(status) else "abstract" if "abstract" in str(status).lower()
                    else "exact_table" if "table" in str(status).lower() else "text"),
        Source_location=r.Source_location, Quality_note=note, Category=cat, Use_group=grp, Model_Set=mset,
        Other_reinforcement=r.Other_reinforcement if pd.notna(r.Other_reinforcement) else "", Verification=V_OLD,
        _cite=r.Citation, _doi=r.DOI if pd.notna(r.DOI) else None))
old = pd.DataFrame(old_rows)

new = pd.DataFrame(new_rows)
meta_all = {**OLD_META, **{k: dict(psize=v["psize"], psize_note=v["psize_note"], melt=v["melt"], rpm=v["rpm"], preheat=v["preheat"]) for k, v in NEW_PAPERS.items()}}
new["_cite"] = new.Paper_ID.map(lambda p: NEW_PAPERS[p]["cite"])
new["_doi"] = new.Paper_ID.map(lambda p: NEW_PAPERS[p]["doi"])
df = pd.concat([old, new], ignore_index=True)

# fill old DOI/citation from DOI embedded in citation
doi_fix = {"P01": "10.1007/s42452-026-08349-y", "N01": "10.1016/j.matpr.2019.09.068", "P04": "10.1007/s42452-024-06192-7",
           "N02": "10.31031/RMES.2017.02.000549", "N17": "10.3389/fmats.2024.1415907"}
df["DOI"] = [d if isinstance(d, str) and d else doi_fix.get(p) for d, p in zip(df._doi, df.Paper_ID)]
df["Citation"] = df._cite.str.replace(r",?\s*DOI:\S+", "", regex=True)
df["Process"] = [NEW_PAPERS[p]["process"] if p in NEW_PAPERS else "Stir casting" for p in df.Paper_ID]
df.loc[df.Paper_ID.isin(["N07"]), "Process"] = "Liquid metal stir casting"
df.loc[df.Paper_ID == "N08", "Process"] = "Two-step stir casting"
df["Process_family"] = [NEW_PAPERS[p]["pfam"] if p in NEW_PAPERS else "Casting (stir)" for p in df.Paper_ID]
df["Particle_size_um"] = df.Paper_ID.map(lambda p: meta_all[p]["psize"])
df["Particle_size_note"] = df.Paper_ID.map(lambda p: meta_all[p]["psize_note"])
df["Melt_T_C"] = df.Paper_ID.map(lambda p: meta_all[p]["melt"])
df["Stir_rpm"] = df.Paper_ID.map(lambda p: meta_all[p]["rpm"])
df["Preheat_SiC_T_C"] = df.Paper_ID.map(lambda p: meta_all[p]["preheat"])
df["Matrix"] = "Al6061"
df["Source_URL"] = [source_url(p, d) for p, d in zip(df.Paper_ID, df.DOI)]

# SiC wt% (reported or derived)
def wt(r):
    if r.SiC_basis == "wt%":
        return r.SiC_native, "reported"
    return round(vol_to_wt(r.SiC_native), 2), f"DERIVED from vol% (rho_Al={RHO_AL}, rho_SiC={RHO_SIC} g/cm3 assumed)"
w = df.apply(wt, axis=1, result_type="expand")
df["SiC_wt_pct"], df["SiC_wt_basis"] = w[0], w[1]

df["Obs_ID"] = df.groupby("Paper_ID").cumcount().add(1).map("{:03d}".format)
df["Obs_ID"] = df.Paper_ID + "-" + df.Obs_ID
cols = ["Obs_ID", "Paper_ID", "Citation", "DOI", "Source_URL", "Category", "Use_group", "Model_Set", "Matrix", "SiC_native", "SiC_basis",
        "SiC_wt_pct", "SiC_wt_basis", "Other_reinforcement", "Process", "Process_family", "Particle_size_um", "Particle_size_note",
        "Melt_T_C", "Stir_rpm", "Preheat_SiC_T_C", "Heat_treatment", "HT_class", "Aging_T_C", "Aging_time_h", "Test_condition",
        "Property", "Value", "Unit", "Hardness_scale", "Data_status", "Value_type", "Source_location", "Quality_note", "Verification"]
df = df[cols]
assert not df.duplicated(["Paper_ID", "SiC_native", "Property", "Value", "HT_class", "Aging_T_C", "Aging_time_h", "Test_condition"]).any()

# ------------------------------------------------------------------ paper index
LIST20 = [  # user's list (message of 2026-11-10); n, id, citation, doi, disposition, reason
 (1, "U01", "Bhat & Kakandikar (2019)", "10.1051/mfreview/2019021", "Extracted (supplementary)", "Binary Al6061-5wt%SiC; only Brinell hardness (81 vs 135 HB) - no tensile data."),
 (2, "U02", "Hu et al. (2019), Materials 12:1602", "10.3390/ma12101602", "Candidate - FIGURE-ONLY data", "Binary SiCp/6061, 0-30 wt% in 5% steps, vacuum hot-press + T6, tensile at RT/100/200 C. UTS/elongation only in Figs 9-10; digitising needed (graph-digitised status). No hardness."),
 (3, "U03", "Jayashree et al. (2020)", "10.1016/j.jmrt.2020.01.098", "Category D - not extracted", "TIG-welded Al6061-SiC; homogenisation/aging. Welding family."),
 (4, "U04", "Selvam et al. (2013)", "10.1016/j.egypro.2013.06.795", "Category C - not extracted", "Fly ash + SiC hybrid."),
 (5, "U05", "Karakoc et al. (2019)", "10.1016/j.jmrt.2019.09.002", "Category C/D - not extracted", "SiC + B4C hybrid, powder metallurgy."),
 (6, "U06", "Gireesh et al. (2018)", "10.3390/jcs2030049", "Category C - not extracted", "Hybrid Al6061 composite (title only screened)."),
 (7, "U07", "Aperador et al. (2024)", "10.3390/met14121462", "Unverified matrix - not extracted", "Al-SiC vs AA2024 by powder metallurgy; matrix of the Al-SiC composite not confirmed as 6061."),
 (8, "U08", "Ishfaq et al. (2020)", "10.1007/s00170-020-06218-5", "Candidate - page not retrievable", "Al6061-7.5%SiC squeeze cast; WEDM machining paper; mechanical data unlikely to be the focus."),
 (9, "U09", "Soliman (2025)", "10.1038/s41598-025-89041-w", "Category F - simulation", "FEA K_I only; no measured UTS/YS/EL/hardness."),
 (10, "U10", "Bhatti et al. (2024)", "10.1016/j.jmrt.2024.09.195", "Category D - not extracted", "High strain-rate compression of SiCp/Al-6061; not quasi-static tensile."),
 (11, "U11", "Leszczynska-Madej et al. (2023)", "10.1007/s43452-023-00771-y", "Unverified matrix - not extracted", "Al-SiC by SPS with high SiC; matrix not confirmed as 6061; tribology focus."),
 (12, "U12", "Sonker et al. (2023)", "10.1007/s43939-023-00045-7", "Category C - not extracted", "Zn/SiC hybrid."),
 (13, "U13", "Perumal et al. (2025)", "10.1007/s42452-025-06687-x", "Category C - not extracted", "Al/SiC/Al2O3 and Al/SiC/TiO2 hybrids."),
 (14, "P04", "Demisie et al. (2024)", "10.1007/s42452-024-06192-7", "Extracted earlier (supplementary)", "Hybrid paper; only single-reinforcement control rows kept."),
 (15, "U15", "Bagasse/aloe vera ash wear study (2025)", "10.1007/s43939-025-00251-5", "Category C - not extracted", "Hybrid, wear focus."),
 (16, "U16", "Sabry (2025)", "10.1007/s00170-025-15627-3", "Category D - not extracted", "Dissimilar friction stir welding AA6061/AA6082."),
 (17, "P01", "Kumar et al. (2026)", "10.1007/s42452-026-08349-y", "Extracted earlier (core)", "Binary series kept; graphite hybrids excluded."),
 (18, "U18", "K. N. et al. (2026)", "10.1007/s42452-026-08382-x", "Category C - not extracted", "SiC-graphite hybrid."),
 (19, "U19", "Shetty et al. (2026)", "10.1007/s42452-026-09213-9", "Category E - excluded", "Al-Si eutectic matrix, not Al6061."),
 (20, "U20", "Prabakaran et al. (2026)", "10.1186/s44147-026-00977-w", "Category C - not extracted", "WS2/WSe2 hybrid."),
]
pi = []
for n, pid, cit, doi, disp, why in LIST20:
    pi.append(dict(Paper_ID=pid, Citation=cit, DOI=doi, Source_list="User 20-paper list #%d" % n, Disposition=disp, Reason=why))
extra = [
 ("N01", "Sivananthan et al. (2020)", "10.1016/j.matpr.2019.09.068", "v4 workbook", "Extracted earlier (core)", "Binary stir-cast 0/2/4 wt%."),
 ("N02", "Agnihotri & Dagar (2017)", "10.31031/RMES.2017.02.000549", "v4 workbook", "Extracted earlier (sensitivity)", "Implausibly low UTS 39-56 MPa."),
 ("N03", "Dilip Raja et al. (2022)", "10.4273/ijvss.14.6.16", "v4 workbook", "Extracted earlier (single point)", "HT condition of 329 MPa unknown."),
 ("N07", "Singh et al. (2023)", "10.1155/2023/2131077", "v4 workbook", "Extracted earlier (supplementary)", "3 of 6 rows derived from % improvements."),
 ("N08", "Two-step stir casting (2026)", "10.1080/0371750X.2026.2655349", "v4 workbook", "Extracted earlier (single point)", "Abstract only."),
 ("N17", "Murmu et al. (2024)", "10.3389/fmats.2024.1415907", "v4 workbook", "Extracted earlier (hybrid)", "Al6061-SiC-fly ash; HRH."),
 ("N18", "Appendino et al. (1991)", "10.1016/0921-5093(91)90575-8", "v4 workbook", "Candidate - not retrieved", "14 vol% SiC T4/T6 aging; full tables needed."),
 ("N19", "Appendino et al. (1995)", "10.1016/0921-5093(94)09740-2", "v4 workbook", "Candidate - not retrieved (HIGH PRIORITY)", "0-20 vol% x 3 sizes x NA/PA/OA aging; tensile/YS/EL. Full text needed."),
 ("N20", "Maurya et al. (2020)", "10.1016/j.matpr.2019.09.003", "v4 workbook", "Candidate - not retrieved", "0-5 wt% stir cast; composite tables needed."),
 ("N21", "Mantha et al. (2024), Adv. Eng. Mater.", "10.1002/adem.202401997", "v4 + this session", "Candidate - abstract only", "Only +33% hardness/UTS, -42% elongation (not assigned to a composition). No absolute values."),
 ("N24", "Rajasekaran et al. (2012)", "10.5402/2012/374719", "This session (search)", "Extracted (core, aging series)", "15 vol% SiC, 23 um; Brinell vs T4/T6 aging, Tables 2-3."),
 ("N25", "Zhang et al. (2016)", "10.3390/ma9060407", "This session (search)", "Extracted (process-specific)", "Powder thixoforming 10 vol% SiC; UTS/YS 230/128."),
 ("N26", "Melik et al. (2022)", "10.37934/mjcsm.9.1.2234", "This session (search)", "Extracted (process-specific)", "PM, 7.5 wt% nano-SiC; HV vs sintering temp."),
 ("N27", "Hassan & Ramadan (2022)", "10.24297/j.cims.2022.12.74", "This session (search)", "Extracted (core HV; supplementary UTS)", "0/1/3/5 wt% stir cast."),
 ("N28", "Srivastava (2026)", "(none)", "This session (search)", "Extracted (supplementary, credibility flag)", "5-20 wt% T6, full Table 1; source credibility unverified."),
 ("N29", "Cascaded-bar Al6061/SiC (Cogent Eng. 2024)", "10.1080/23311916.2024.2315826", "This session (search)", "Extracted (process-specific, compression)", "Title/authors not retrieved."),
 ("N31", "Ultrasonic-cast Al6061/SiC, J. Sci. Technol. Compos. (2025)", "10.22068/jstc.2025.2067571.1932", "This session (search)", "Candidate - no numeric values on page", "Only +20% hardness reported."),
]
for pid, cit, doi, src, disp, why in extra:
    pi.append(dict(Paper_ID=pid, Citation=cit, DOI=doi, Source_list=src, Disposition=disp, Reason=why))
paper_index = pd.DataFrame(pi)
paper_index["Source_URL"] = [source_url(p, d) for p, d in zip(paper_index.Paper_ID, paper_index.DOI)]
cnt = df.groupby("Paper_ID").agg(Rows=("Obs_ID", "count"), Categories=("Category", lambda s: ",".join(sorted(set(s))))).reset_index()
paper_index = paper_index.merge(cnt, on="Paper_ID", how="left")
paper_index["Rows"] = paper_index["Rows"].fillna(0).astype(int)

excl = pd.DataFrame([
 ("N22", "Appendino et al. (1990)", "10.1016/0254-0584(90)90007-W", "E/morphology", "SiC whisker (not particulate); no target property series."),
 ("N23", "Murmu et al. (2024) duplicate entry", "10.3389/fmats.2024.1415907", "Duplicate", "Same article as N17."),
 ("R01", "Review: AA6061 MMCs by stir casting (2021)", "10.3390/ma14010175", "Review", "Not an independent dataset."),
 ("R02", "Review: MMC manufacturing routes (2023)", "PMC9950845", "Review", "Process taxonomy only."),
 ("N30", "Mantha et al. (2024) J. Manuf. Mater. Process. 8(6):245", "10.3390/jmmp8060245", "E/not SiC", "Al6061-CuO composite - not SiC. Do not confuse with Mantha et al. Adv. Eng. Mater. (SiC)."),
 ("S01", "SiC/AA2024 nanocomposites, PM + T6 (PMC9145340)", "-", "E", "AA2024 matrix. Screened from search snippet only."),
 ("S02", "SiC-reinforced AZ91 (PMC7672630)", "-", "E", "Mg matrix. Snippet only."),
 ("S03", "Al6061/TiO2 microcomposites (PMC9144662)", "-", "E/not SiC", "TiO2 reinforcement. Snippet only."),
 ("S04", "Al-6061 + particulate waste glass (S2468227621001162)", "-", "E/not SiC", "Glass reinforcement. Snippet only."),
 ("S05", "FSW SiC and B4C reinforced AA6061 (PMC8200972)", "-", "C/D", "Hybrid + welding. Snippet only."),
 ("S06", "SiC-Gr/Al6061 hybrid (10.1007/s42452-020-2713-4)", "10.1007/s42452-020-2713-4", "C", "Graphite hybrid. Snippet only."),
 ("S07", "Al6061-SiC-B4C stir cast (10.1007/s40033-024-00649-0)", "10.1007/s40033-024-00649-0", "C", "B4C hybrid. Snippet only."),
 ("S08", "SiC nanowires / 6061Al (PMC9738129)", "-", "E/morphology", "Nanowires, not particulate. Page not fetched; title only."),
 ("S09", "Wrought/other-matrix patents and handbook hits", "-", "E", "Patents, not experimental papers."),
], columns=["Paper_ID", "Citation", "DOI", "Category", "Reason"])
for _, r in paper_index[paper_index.Disposition.str.contains("Category [CDEF]|excluded", regex=True)].iterrows():
    excl.loc[len(excl)] = [r.Paper_ID, r.Citation, r.DOI, r.Disposition, r.Reason]

# ------------------------------------------------------------------ provenance / checks / coverage
prov = []
for pid, g in df.groupby("Paper_ID"):
    prov.append(dict(Paper_ID=pid, Citation=g.Citation.iloc[0], Rows=len(g), Extraction_method=g.Verification.iloc[0],
                     Value_types=", ".join(sorted(set(g.Value_type))), Source_locations="; ".join(sorted(set(g.Source_location.astype(str))))[:300]))
prov = pd.DataFrame(prov)

miss = []
for pid, g in df[df.Category.isin(["A", "B", "D"])].groupby("Paper_ID"):
    row = dict(Paper_ID=pid, Rows=len(g), Category=",".join(sorted(set(g.Category))))
    for c in ["Particle_size_um", "Melt_T_C", "Stir_rpm", "Preheat_SiC_T_C"]:
        row[c + "_missing_pct"] = round(100 * g[c].isna().mean())
    row["HT_class"] = ", ".join(sorted(set(g.HT_class)))
    miss.append(row)
miss = pd.DataFrame(miss)

def cov(g):
    return pd.Series(dict(Observations=len(g), Independent_papers=g.Paper_ID.nunique(), Papers=", ".join(sorted(g.Paper_ID.unique())),
                          SiC_wt_min=g.SiC_wt_pct.min(), SiC_wt_max=g.SiC_wt_pct.max()))
coverage = df.groupby(["Category", "Model_Set", "Property"]).apply(cov, include_groups=False).reset_index()

dups = pd.DataFrame(dup_rows)

# ------------------------------------------------------------------ write
sim_cols = df[df.Category == "F"]
sheets = {
 "START_HERE": None,
 "Master_Core_Experimental_Data": df[df.Category == "A"],
 "Supplementary_Binary_Data": df[df.Category == "B"],
 "Hybrid_Composite_Data": df[df.Category == "C"],
 "Process_Specific_Data": df[df.Category == "D"],
 "Simulation_Data": sim_cols,
 "Excluded_Papers": excl,
 "Paper_Index": paper_index,
 "Data_Provenance": prov,
 "Missing_Data_Checks": miss,
 "Dataset_Coverage": coverage,
 "Duplicate_Checks": dups,
}
n_core = (df.Category == "A").sum()
start = pd.DataFrame({"Item": [
 "Purpose", "Version", "Rows in this workbook (unique observations)", "Category A rows", "  of which Model_Set=Primary (as-cast, trainable)",
 "  of which Model_Set=Aging-only (Rajasekaran, one paper)", "Category B rows", "Category C rows", "Category D rows", "Category F rows",
 "v4 rows in -> after dedupe", "Unit of 'independent'", "Verification level", "IMPORTANT",
 "Units/scales", "wt% vs vol%", "Not yet retrieved"],
 "Value": [
 "Traceable, categorised Al6061-SiC literature observations; one row = one property observation.",
 "v5 (batch 1) built 2026-11-10 from v4 workbook + 9 newly read papers",
 len(df), n_core, int(((df.Category == "A") & (df.Model_Set == "Primary")).sum()),
 int(((df.Category == "A") & (df.Model_Set == "Aging-only")).sum()), int((df.Category == "B").sum()), int((df.Category == "C").sum()),
 int((df.Category == "D").sum()), int((df.Category == "F").sum()),
 f"{n_v4_in} in All_Records, {len(all_rec)} after dedupe; {len(new_v4)} rows in New_Records_v4 were duplicates of N17",
 "Papers, not rows. Rows within a paper are not independent.",
 "v4-inherited rows: carried over unchanged (original PDFs not available in this session). New rows: read via web-text extraction, NOT visually checked against PDFs.",
 "Rows are NOT 'verified experiments'. Check Category, Model_Set and Verification columns before using any row.",
 "Vickers, Brinell, Rockwell never mixed. Brinell from Rajasekaran converted MPa->kgf/mm2 (flagged).",
 f"Rajasekaran 15 vol% is also given as DERIVED wt% using rho_Al={RHO_AL}, rho_SiC={RHO_SIC}; the derived basis is stated in SiC_wt_basis.",
 "Appendino 1991/1995, Maurya 2020, Mantha 2024 (absolute values), Hu 2019 (figure-only: needs digitising), Ishfaq 2020, Jayashree 2020, remaining hybrids/welding papers (not needed for binary dataset)."]})
with pd.ExcelWriter(OUT_X, engine="openpyxl") as xw:
    for name, d in sheets.items():
        (start if d is None else d).to_excel(xw, sheet_name=name, index=False)
    from openpyxl.styles import Font, PatternFill, Alignment
    for ws in xw.book.worksheets:
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F3864")
            c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        for i, col in enumerate(ws.columns, 1):
            m = max((len(str(c.value)) for c in col[:60] if c.value is not None), default=8)
            ws.column_dimensions[ws.cell(1, i).column_letter].width = min(max(10, m + 2), 60)

paper_index.to_csv(ROOT / "data/Paper_Index_v5.csv", index=False)
df.to_csv(OUT_ALL, index=False)
df[(df.Category == "A") & (df.Model_Set == "Primary")].to_csv(OUT_CORE, index=False)
print("rows", len(df)); print(df.groupby(["Category", "Model_Set"]).size())
print(coverage[coverage.Category == "A"].to_string())
print("wrote", OUT_X)

"""New observations added in v5 (batch 1, 2026-11-10).

Every value below was read from the cited open-access page through a text-extraction
tool; none has been checked against the PDF by eye. Verification field says so.
Nothing is estimated from figures. Rule 12 statuses are used throughout.
"""

V_WEB = "Web-fetch text extraction 2026-11-10; not visually checked against PDF"

# ---------------- paper-level metadata (new papers) ----------------
NEW_PAPERS = {
    "N24": dict(cite="Rajasekaran et al. (2012), ISRN Materials Science (Hindawi/Wiley), 'T4 and T6 Treatment of 6061 Al-15 Vol.% SiCp Composite'",
                doi="10.5402/2012/374719", psize=23, psize_note="23 um", melt=None, rpm=None, preheat=None,
                process="Stir casting + extrusion", pfam="Casting (stir)"),
    "N25": dict(cite="Zhang, Chen, Qin & Wang (2016), Materials 9(6):407, 'Comparative study on permanent mold cast and powder thixoforming 6061 Al alloy and SiCp/6061Al composite'",
                doi="10.3390/ma9060407", psize=6.94, psize_note="6.94 um average", melt=None, rpm=None, preheat=None,
                process="Powder thixoforming (composite/PTF alloy); permanent mold casting (PMC alloy)", pfam="Semi-solid / powder"),
    "N26": dict(cite="Melik, Boumerzoug & Delaunois (2022), Malaysian J. Composites Sci. Manuf. 9(1):22-34, 'Characterization of the Al6061 Alloy Reinforced with SiC Nanoparticles ... Powder Metallurgy'",
                doi="10.37934/mjcsm.9.1.2234", psize=0.05, psize_note="0.05 um (nano SiC), Table 2", melt=None, rpm=None, preheat=None,
                process="Powder metallurgy (ball mill 300 rpm 2 h, 10 t compaction, sintered 2 h Ar/H2)", pfam="Powder metallurgy"),
    "N27": dict(cite="Hassan & Ramadan (2022), Computer Integrated Manufacturing Systems 28(12), Al6061-SiC stir casting, wear & mechanical",
                doi="10.24297/j.cims.2022.12.74", psize=None, psize_note="1-13 um", melt=825, rpm=600, preheat=250,
                process="Stir casting (melt 800-850 C, 600 rpm ~10 min, 1% Mg)", pfam="Casting (stir)"),
    "N28": dict(cite="Srivastava (2026), Int. J. Advanced Multidisciplinary Application 3(5), 'Fatigue Behaviour, Tribological Performance and Failure Analysis of Al-SiC MMCs'",
                doi=None, psize=30, psize_note="30 +/- 5 um", melt=750, rpm=400, preheat=900,
                process="Double-pass electromagnetic stir casting (400 rpm equivalent, 0.5% Mg)", pfam="Casting (stir)"),
    "N29": dict(cite="Cascaded compound-bar Al6061/SiC study, Cogent Engineering (2024) - title/authors NOT retrieved (DOI taken from URL)",
                doi="10.1080/23311916.2024.2315826", psize=None, psize_note="15-35 um", melt=None, rpm=None, preheat=None,
                process="Stir-cast cascaded compound bars (Al6061-T6 casing / SiC composite core), homogenised 500 C 8 h", pfam="Casting (stir)"),
    "U01": dict(cite="Bhat & Kakandikar (2019), Manufacturing Review 6:24, 'Manufacture of SiC reinforced aluminium 6061 MMCs for enhanced sliding wear properties'",
                doi="10.1051/mfreview/2019021", psize=None, psize_note="paper prints '50 mm' (typo, likely um) - NOT used", melt=750, rpm=500, preheat=250,
                process="Stir casting (1% Mg, 1% flux)", pfam="Casting (stir)"),
    "U09": dict(cite="Soliman (2025), Scientific Reports 15:5763, 'Fracture mechanics for compact tensile specimen of Al6061-SiC MMC' (FEA)",
                doi="10.1038/s41598-025-89041-w", psize=None, psize_note="not reported", melt=None, rpm=None, preheat=None,
                process="Finite-element simulation (ANSYS); no specimens made", pfam="Simulation"),
}

# row template: dict(paper, sic_native, basis, prop, value, unit, scale, ht, ht_class, aging_T, aging_h, cond, status, vtype, loc, note, cat, group, model)
def R(paper, sic, basis, prop, val, unit, status, vtype, loc, note, cat, group, model,
      ht="Not reported (as-cast)", htc="As-cast", ageT=None, ageh=None, cond="", scale=None, other=""):
    return dict(Paper_ID=paper, SiC_native=sic, SiC_basis=basis, Property=prop, Value=val, Unit=unit,
                Hardness_scale=scale, Heat_treatment=ht, HT_class=htc, Aging_T_C=ageT, Aging_time_h=ageh,
                Test_condition=cond, Data_status=status, Value_type=vtype, Source_location=loc,
                Quality_note=note, Category=cat, Use_group=group, Model_Set=model,
                Other_reinforcement=other, Verification=V_WEB)

new_rows = []

# ---- N24 Rajasekaran 2012: Brinell vs aging time (15 vol% SiC, 23 um) ----
t4_t = [0, 3, 6, 12, 24, 48, 120, 240, 480, 720, 1440]
t4_hb = [91, 101, 106, 108, 109, 110, 112, 112, 113, 113, 112]
for t, hb in zip(t4_t, t4_hb):
    if t == 0:
        new_rows.append(R("N24", 15, "vol%", "Brinell_HB", hb, "kgf/mm2", "Exact table value", "exact_table",
            "Table 2 (t=0) = Table 3 (t=0)", "Solution treated 558 C/1 h + water quench, 0 h aging. Shared start point of T4 and T6 series; stored once.",
            "A", "Core_aging_series", "Aging-only", ht="Solution 558 C 1 h, water quench", htc="Solution+WQ", ageh=0,
            scale="Brinell"))
    else:
        new_rows.append(R("N24", 15, "vol%", "Brinell_HB", hb, "kgf/mm2", "Exact table value", "exact_table",
            "Table 2", "T4 = natural aging at room temperature after solution treatment. Paper text and Conclusion disagree on T4 peak (1107.4 vs ~1097 MPa); table values used.",
            "A", "Core_aging_series", "Aging-only", ht="Solution 558 C 1 h, WQ, natural aging (T4)", htc="T4", ageh=t, scale="Brinell"))

t6_times = [0.5, 1, 2, 3, 4, 5, 6, 8, 10, 20]
t6_mpa = {  # Table 3, Brinell hardness in MPa
 140: [1097.6,1156.4,1195.6,1215.2,1244.6,1264.2,1274,1254.4,1234.8,1117.2],
 160: [1166.2,1225,1293.6,1313.2,1323,1352.4,1313.2,1225,1185.8,1136.8],
 180: [1244.6,1313.2,1401.4,1430.8,1450.4,1401.4,1352.4,1303.4,1244.6,1146.6],
 200: [1234.8,1332.8,1372,1401.4,1342.6,1323,1264.2,1205.4,1185.8,1127],
 220: [1205.4,1283.8,1362.2,1332.8,1313.2,1283.8,1234.8,1205.4,1185.8,1136.8],
 240: [1195.6,1254.4,1274,1254.4,1244.6,1215.2,1195.6,1185.8,1176,1127],
}
for T, arr in t6_mpa.items():
    for t, m in zip(t6_times, arr):
        new_rows.append(R("N24", 15, "vol%", "Brinell_HB", round(m/9.80665, 1), "kgf/mm2", "Exact table value, unit-converted (MPa / 9.80665)", "exact_table_converted",
            "Table 3", f"Reported as {m} MPa; converted to kgf/mm2 (checked: 893.7 MPa -> 91, 1107.4 -> 113 match Table 2).",
            "A", "Core_aging_series", "Aging-only", ht="Solution 558 C 1 h, WQ, artificial aging (T6)", htc="T6", ageT=T, ageh=t, scale="Brinell"))

# ---- N25 Zhang 2016 ----
for mat, sic, uts, ys, el, proc in [
    ("PMC 6061 (no SiC)", 0, 120, 59, None, "Permanent mold casting"),
    ("PTF 6061 (no SiC)", 0, 180, 99, 8.0, "Powder thixoforming"),
    ("PTF SiCp/6061", 10, 230, 128, None, "Powder thixoforming + 40 min ball milling")]:
    for prop, v, u, loc in [("UTS_MPa", uts, "MPa", "Abstract; Section 3.3; Fig. 5"), ("Yield_strength_MPa", ys, "MPa", "Section 3.3; Fig. 5"), ("Elongation_pct", el, "%", "Section 3.3 text")]:
        if v is None: continue
        new_rows.append(R("N25", sic, "vol%", prop, v, u, "Exact text value", "text", loc,
            f"{mat}; {proc}. No solution/aging treatment reported (only partial remelting 933 K 90 min). Fig. 5 not read. Elongation 8.0% is stated as 'maximum of the three'.",
            "D", "Process_specific", "No", ht="None (powder: partial remelt 933 K/90 min)", htc="Not heat-treated"))

# ---- N26 Melik 2022 (HV5 vs sintering temp) ----
for T, v, loc in [(600, 32.2, "Section 3.5, Fig. 8; Abstract"), (630, 19.4, "Conclusion (5)")]:
    new_rows.append(R("N26", 7.5, "wt%", "Vickers_HV", v, "HV5", "Exact text value", "text", loc,
        f"Sintered at {T} C, 2 h. Nano-SiC 0.05 um; HV5 (5 kgf), 6 indents. 31.0 HV (Conclusion) not assigned to a temperature in the text -> omitted.",
        "D", "Process_specific", "No", ht=f"Sintering {T} C/2 h", htc="Sintered", cond=f"Sintering T={T} C", scale="Vickers"))

# ---- N27 Hassan & Ramadan 2022 ----
for sic, v, loc, note in [(0, 81, "Results text; Fig. 12", "Table 2 of paper lists 100 HV for Al6061 (handbook value); measured baseline 81 HV used."),
                          (1, 83.175, "Results text; Fig. 12", ""),
                          (5, 92.74, "Results text; Fig. 12", "Stated as highest hardness.")]:
    new_rows.append(R("N27", sic, "wt%", "Vickers_HV", v, "HV", "Exact text value (figure-backed)", "text", loc,
        "Stir cast, 1% Mg, as-cast. 3 wt% hardness omitted: text says 'from 81 to 91.62 HV' (ambiguous). " + note,
        "A", "Core_candidate", "Primary", scale="Vickers"))
for sic, v, note in [(0, 126.26, ""), (1, 165, ""), (3, 115, "Text claims 3 and 5 wt% fall ~30% below 1 wt%; 5 wt% never given numerically -> omitted.")]:
    new_rows.append(R("N27", sic, "wt%", "UTS_MPa", v, "MPa", "Exact text value (figure-backed)", "text", "Results text; Figs. 10-11",
        "Mean of 3 specimens. Paper-internal inconsistency in the UTS trend; held back as supplementary. " + note,
        "B", "Supplementary_binary", "Sensitivity"))

# ---- N28 Srivastava 2026 (flagged credibility) ----
tbl = {
 "UTS_MPa": ("MPa", [312, 341, 368, 398, 374], [8, 7, 9, 6, 11], None),
 "Yield_strength_MPa": ("MPa", [276, 298, 321, 348, 335], [6, 5, 8, 7, 9], None),
 "Elongation_pct": ("%", [10.2, 8.1, 6.3, 4.2, 2.9], [0.8, 0.6, 0.5, 0.4, 0.6], None),
 "Brinell_HB": ("BHN", [95, 112, 128, 147, 162], [4, 3, 4, 3, 5], "Brinell"),
}
for prop, (u, vals, sds, sc) in tbl.items():
    for sic, v, sd in zip([0, 5, 10, 15, 20], vals, sds):
        new_rows.append(R("N28", sic, "wt%", prop, v, u, "Exact table value", "exact_table", "Table 1, Section 3.2",
            f"+/-{sd} (as printed). T6 (530 C/4 h, 175 C/8 h). CREDIBILITY FLAG: low-profile journal, no DOI, no data-availability statement, control equals handbook T6 6061 (312/276), "
            "unusually smooth trends. Needs independent verification before primary use.",
            "B", "Supplementary_flagged_credibility", "Sensitivity", ht="T6: 530 C/4 h solution + 175 C/8 h aging", htc="T6", ageT=175, ageh=8, scale=sc))

# ---- N29 cascaded bars (compression only) ----
for sic, v in [(2, 530.70), (4, 589.35), (6, 691.88)]:
    new_rows.append(R("N29", sic, "wt%", "Compressive_strength_MPa", v, "MPa", "Exact text value", "text", "Section 1 / 3.2.1 (table no. not recoverable)",
        "Composite core of compound bar, homogenised 500 C/8 h. Compression, not tensile - not a target property. Title/authors not retrieved.",
        "D", "Process_specific", "No", ht="Homogenised 500 C/8 h, furnace cool", htc="Homogenised"))

# ---- U01 Bhat 2019 ----
for sic, v in [(0, 81), (5, 135)]:
    new_rows.append(R("U01", sic, "wt%", "Brinell_HB", v, "HB", "Exact text value", "text", "Section 3; Fig. 4",
        "Rockwell tester (100 kg, ball) converted to Brinell by authors; individual readings not tabulated. Brinell kept separate from Vickers.",
        "B", "Supplementary_binary", "Sensitivity", scale="Brinell (converted from Rockwell)"))

# ---- U09 Soliman 2025 FEA ----
ki = {0: (296.72, 353.59, 420.49), 4: (283.31, 337.13, 400.64), 6: (282.49, 336.12, 399.43),
      10: (281.68, 335.12, 398.23), 12: (281.14, 334.46, 397.43), 14: (280.6, 333.8, 396.63)}
for sic, vals in ki.items():
    for ah, v in zip([0.35, 0.43, 0.5], vals):
        new_rows.append(R("U09", sic, "vol%", "FEA_KI_MPa_mm05", v, "MPa*mm^0.5", "Simulation output (not measured)", "simulation", "Table 4",
            "ANSYS mode-I stress intensity factor at P=603 N; NOT a measured fracture toughness and not a target property.",
            "F", "Simulation", "No", cond=f"a/H={ah}"))

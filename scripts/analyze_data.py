"""Phase 3: dataset analysis + plots.  Run: python scripts/analyze_data.py"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports/figures"; FIG.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(ROOT / "data/Al6061_SiC_Master_Dataset_v5.csv")

# binary single-reinforcement, as-cast / not heat-treated, non-hybrid, non-simulation
bin_ = df[df.Category.isin(["A", "B"]) & df.HT_class.isin(["As-cast", "Unknown (before/after HT not specified)"])
          & (df.Value_type != "calculated")].copy()
TARGETS = [("UTS_MPa", "UTS (MPa)"), ("Yield_strength_MPa", "Yield strength (MPa)"),
           ("Elongation_pct", "Elongation (%)"), ("Vickers_HV", "Vickers hardness (HV)")]
papers = sorted(bin_.Paper_ID.unique())
marks = ["o", "s", "^", "D", "v", "P", "X", "*", "h", "<", ">"]
mk = {p: marks[i % len(marks)] for i, p in enumerate(papers)}
cols = plt.get_cmap("tab10")
pcol = {p: cols(i % 10) for i, p in enumerate(papers)}

fig, axs = plt.subplots(2, 2, figsize=(12, 9))
for ax, (prop, lab) in zip(axs.ravel(), TARGETS):
    d = bin_[bin_.Property == prop]
    for p, g in d.groupby("Paper_ID"):
        core = (g.Category == "A") & (g.Model_Set == "Primary")
        if core.any():
            ax.scatter(g.SiC_wt_pct[core], g.Value[core], marker=mk[p], color=pcol[p], s=55, label=f"{p} (core)")
        if (~core).any():
            ax.scatter(g.SiC_wt_pct[~core], g.Value[~core], marker=mk[p], facecolors="none", edgecolors=pcol[p], s=55, label=f"{p} (suppl.)")
    ax.set_xlabel("SiC (wt.%)"); ax.set_ylabel(lab); ax.grid(alpha=.3)
    ax.set_title(f"{lab}: {d.Paper_ID.nunique()} papers, {len(d)} obs")
    ax.legend(fontsize=7, ncol=2)
fig.suptitle("Binary Al6061-SiC, as-cast — filled = core, hollow = supplementary (not used for training)")
fig.tight_layout(); fig.savefig(FIG / "scatter_four_targets.png", dpi=150); plt.close(fig)

# one figure per target (as requested), plus Brinell separate (different scale)
for prop, lab in TARGETS:
    fig, ax = plt.subplots(figsize=(6, 4.2))
    for p, g in bin_[bin_.Property == prop].groupby("Paper_ID"):
        ax.scatter(g.SiC_wt_pct, g.Value, marker=mk[p], color=pcol[p], s=50, label=p)
    ax.set_xlabel("SiC (wt.%)"); ax.set_ylabel(lab); ax.grid(alpha=.3); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / f"scatter_{prop}.png", dpi=150); plt.close(fig)

br = df[(df.Property == "Brinell_HB") & df.Category.isin(["A", "B"]) & (df.Value_type != "calculated")
        & ~df.Paper_ID.isin(["N24"])]
fig, ax = plt.subplots(figsize=(6, 4.2))
for p, g in br.groupby("Paper_ID"):
    ax.scatter(g.SiC_wt_pct, g.Value, s=50, label=f"{p} ({g.HT_class.iloc[0]})")
ax.set_xlabel("SiC (wt.%)"); ax.set_ylabel("Brinell hardness (HB)"); ax.grid(alpha=.3); ax.legend(fontsize=7)
ax.set_title("Brinell (kept separate from Vickers)")
fig.tight_layout(); fig.savefig(FIG / "scatter_Brinell_HB.png", dpi=150); plt.close(fig)

# aging series
n24 = df[df.Paper_ID == "N24"]
fig, ax = plt.subplots(figsize=(6.5, 4.4))
t4 = n24[n24.HT_class.isin(["T4", "Solution+WQ"])]
ax.semilogx(t4.Aging_time_h.replace(0, 0.1), t4.Value, "k-o", label="T4 (room temp.)")
for T, g in n24[n24.HT_class == "T6"].groupby("Aging_T_C"):
    ax.semilogx(g.Aging_time_h, g.Value, "-o", ms=3, label=f"T6 {int(T)} °C")
ax.set_xlabel("Aging time (h)"); ax.set_ylabel("Brinell (kgf/mm²)"); ax.grid(alpha=.3); ax.legend(fontsize=7)
ax.set_title("N24 Rajasekaran 2012: 15 vol.% SiC (≈17.3 wt.%)")
fig.tight_layout(); fig.savefig(FIG / "aging_N24.png", dpi=150); plt.close(fig)

# distributions
fig, axs = plt.subplots(1, 5, figsize=(17, 3.2))
prim = df[(df.Category == "A") & (df.Model_Set == "Primary")]
axs[0].hist(prim.drop_duplicates(["Paper_ID", "SiC_wt_pct"]).SiC_wt_pct, bins=range(0, 17), color="#4C78A8"); axs[0].set_title("SiC wt.% (core compositions)")
for ax, (prop, lab) in zip(axs[1:], TARGETS):
    ax.hist(prim[prim.Property == prop].Value, bins=8, color="#59A14F"); ax.set_title(lab)
fig.tight_layout(); fig.savefig(FIG / "distributions_core.png", dpi=150); plt.close(fig)

# stats / outliers / compatibility
rows = []
for prop, _ in TARGETS:
    for grp, d in [("core_primary", prim[prim.Property == prop]), ("all_binary_ascast", bin_[bin_.Property == prop])]:
        if d.empty: continue
        q1, q3 = d.Value.quantile([.25, .75]); iqr = q3 - q1
        out = d[(d.Value < q1 - 1.5 * iqr) | (d.Value > q3 + 1.5 * iqr)]
        rows.append(dict(Property=prop, Set=grp, N_obs=len(d), N_papers=d.Paper_ID.nunique(), Mean=d.Value.mean(), SD=d.Value.std(),
                         Min=d.Value.min(), Max=d.Value.max(), SiC_min=d.SiC_wt_pct.min(), SiC_max=d.SiC_wt_pct.max(),
                         IQR_outliers=", ".join(out.Obs_ID)))
pd.DataFrame(rows).round(2).to_csv(ROOT / "reports/dataset_statistics.csv", index=False)

# between-paper compatibility: control (0 wt%) values per paper
ctrl = bin_[(bin_.SiC_wt_pct == 0) & bin_.Property.isin([t for t, _ in TARGETS])].pivot_table(index="Paper_ID", columns="Property", values="Value")
ctrl.round(2).to_csv(ROOT / "reports/unreinforced_control_by_paper.csv")
print(pd.read_csv(ROOT / "reports/dataset_statistics.csv").to_string()); print(ctrl.round(1))

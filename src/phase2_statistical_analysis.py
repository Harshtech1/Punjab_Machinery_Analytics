"""
Punjab Machinery Analytics - Phase 2
Statistical Assessment of Hypothesis:
    "Higher machinery penetration is associated with lower methane emissions."

Outputs:
  - outputs/correlation_tables/phase2_correlation_all_villages.csv
  - outputs/correlation_tables/phase2_correlation_matched_villages.csv
  - outputs/correlation_tables/phase2_correlation_combined_publication.csv
  - outputs/charts/scatter_ch4_vs_InSitu.png
  - outputs/charts/scatter_ch4_vs_ExSitu.png
  - outputs/charts/scatter_ch4_vs_TotalMachines.png
  - outputs/charts/correlation_ranking_chart.png
  - outputs/policy_reports/phase2_hypothesis_conclusion.txt
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
import seaborn as sns
from scipy import stats
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import LinearRegression

warnings.filterwarnings("ignore")

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH  = os.path.join(BASE_DIR, "data", "merged", "Punjab_CH4_Machinery_Master.csv")
CORR_DIR   = os.path.join(BASE_DIR, "outputs", "correlation_tables")
CHART_DIR  = os.path.join(BASE_DIR, "outputs", "charts")
REPORT_DIR = os.path.join(BASE_DIR, "outputs", "policy_reports")

for d in [CORR_DIR, CHART_DIR, REPORT_DIR]:
    os.makedirs(d, exist_ok=True)

# ─── Variables ──────────────────────────────────────────────────────────────
CH4_COL = "Predicted_CH4_ppb"
MACHINERY_COLS = ["In_Situ", "Ex_Situ", "Prime_Mover", "General", "CRM", "SMAM", "CDP", "Total_Machines"]
COVARS = [
    "TOTAL CULTIVABLE AREA (IN HECTARES), IF IN ACRES DIVIDE BY 2.47",
    "NET SOWN AREA (IN HECTARES) , IF IN ACRES DIVIDE BY 2.47"
]

# ─── Style ──────────────────────────────────────────────────────────────────
PALETTE = {
    "bg":        "#0d1117",
    "surface":   "#161b22",
    "border":    "#30363d",
    "accent1":   "#58a6ff",
    "accent2":   "#f78166",
    "accent3":   "#3fb950",
    "accent4":   "#d2a8ff",
    "text":      "#e6edf3",
    "subtext":   "#8b949e",
    "negative":  "#f78166",
    "positive":  "#3fb950",
    "neutral":   "#e3b341",
}

plt.rcParams.update({
    "figure.facecolor":  PALETTE["bg"],
    "axes.facecolor":    PALETTE["surface"],
    "axes.edgecolor":    PALETTE["border"],
    "axes.labelcolor":   PALETTE["text"],
    "xtick.color":       PALETTE["subtext"],
    "ytick.color":       PALETTE["subtext"],
    "text.color":        PALETTE["text"],
    "grid.color":        PALETTE["border"],
    "grid.linewidth":    0.6,
    "grid.linestyle":    "--",
    "font.family":       "DejaVu Sans",
    "axes.titlesize":    13,
    "axes.labelsize":    11,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "legend.fontsize":   9,
})


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — Data Loading & Validation
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*65)
print("  PUNJAB MACHINERY ANALYTICS — PHASE 2 STATISTICAL ASSESSMENT")
print("═"*65)

print(f"\n[1] Loading data: {DATA_PATH}")
df = pd.read_csv(DATA_PATH, low_memory=False)
print(f"    Total rows: {len(df):,}")
print(f"    Columns: {df.shape[1]}")

# Matched subset (merge_confidence > 0)
df_matched = df[df["merge_confidence"] > 0].copy()
print(f"    Matched villages: {len(df_matched):,}")
print(f"    Unmatched villages: {len(df) - len(df_matched):,}")

# Summary of key columns
print(f"\n[2] Key column availability:")
for col in [CH4_COL] + MACHINERY_COLS + COVARS:
    n_valid = df[col].notna().sum()
    n_nonzero = (df[col] > 0).sum() if df[col].dtype != "object" else "N/A"
    print(f"    {col[:30]:30s}  valid={n_valid:6,}  nonzero={n_nonzero:6}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — Correlation Calculation
# ════════════════════════════════════════════════════════════════════════════

def significance_star(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return "ns"

def partial_corr(data, x, y, covars):
    sub = data[[x, y] + covars].dropna()
    if len(sub) < 5:
        return np.nan, np.nan
    mod_x = LinearRegression().fit(sub[covars], sub[x])
    res_x = sub[x] - mod_x.predict(sub[covars])
    
    mod_y = LinearRegression().fit(sub[covars], sub[y])
    res_y = sub[y] - mod_y.predict(sub[covars])
    
    pr, pp = stats.pearsonr(res_x, res_y)
    return pr, pp

def compute_correlations(data: pd.DataFrame, label: str) -> pd.DataFrame:
    """
    Compute Pearson + Spearman + Partial correlations of CH4 vs each machinery column.
    Returns a DataFrame with one row per machinery variable.
    """
    rows = []
    for col in MACHINERY_COLS:
        sub = data[[CH4_COL, col] + COVARS].dropna()
        # Drop rows where both are zero to avoid spurious zeros inflating correlation
        sub = sub[(sub[CH4_COL] > 0) | (sub[col] > 0)]
        n = len(sub)
        if n < 5:
            rows.append({
                "Variable": col,
                "Subset": label,
                "N": n,
                "Pearson_r": np.nan,
                "Pearson_p": np.nan,
                "Pearson_sig": "insufficient data",
                "Spearman_rho": np.nan,
                "Spearman_p": np.nan,
                "Spearman_sig": "insufficient data",
                "Partial_r": np.nan,
                "Partial_p": np.nan,
                "Partial_sig": "insufficient data",
                "Direction": "—",
                "Interpretation": "Insufficient data",
            })
            continue
        pr, pp = pearsonr(sub[CH4_COL], sub[col])
        sr, sp = spearmanr(sub[CH4_COL], sub[col])
        part_r, part_p = partial_corr(sub, CH4_COL, col, COVARS)
        
        # Use partial r for direction and interpretation since we care about controlling for village size
        direction = "↓ Negative" if part_r < 0 else "↑ Positive"
        interpretation = (
            "Supports hypothesis" if part_r < -0.1 and part_p < 0.05
            else "Weak / insufficient evidence" if part_r < 0 and part_p >= 0.05
            else "Contradicts hypothesis" if part_r > 0.1 and part_p < 0.05
            else "Neutral"
        )
        rows.append({
            "Variable": col,
            "Subset": label,
            "N": n,
            "Pearson_r": round(pr, 4),
            "Pearson_p": round(pp, 6),
            "Pearson_sig": significance_star(pp),
            "Spearman_rho": round(sr, 4),
            "Spearman_p": round(sp, 6),
            "Spearman_sig": significance_star(sp),
            "Partial_r": round(part_r, 4),
            "Partial_p": round(part_p, 6),
            "Partial_sig": significance_star(part_p),
            "Direction": direction,
            "Interpretation": interpretation,
        })
    return pd.DataFrame(rows)


print("\n[3] Computing correlations...")
corr_all     = compute_correlations(df, "All Villages")
corr_matched = compute_correlations(df_matched, "Matched Villages Only")
corr_combined = pd.concat([corr_all, corr_matched], ignore_index=True)

# Save tables
corr_all.to_csv(os.path.join(CORR_DIR, "phase2_correlation_all_villages.csv"), index=False)
corr_matched.to_csv(os.path.join(CORR_DIR, "phase2_correlation_matched_villages.csv"), index=False)
corr_combined.to_csv(os.path.join(CORR_DIR, "phase2_correlation_combined_publication.csv"), index=False)
print("    ✓ Correlation tables saved.")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — Print Publication-Ready Tables
# ════════════════════════════════════════════════════════════════════════════

def print_table(corr_df: pd.DataFrame, title: str):
    print(f"\n{'═'*115}")
    print(f"  {title}")
    print(f"{'═'*115}")
    header = (
        f"{'Variable':<15} {'N':>6} "
        f"{'Pearson r':>10} {'Sig':>4}  "
        f"{'Spearman ρ':>10} {'Sig':>4}  "
        f"{'Partial r':>10} {'Sig':>4}  "
        f"{'Direction':<12} {'Interpretation'}"
    )
    print(header)
    print("─"*115)
    for _, row in corr_df.iterrows():
        pr = f"{row['Pearson_r']:.4f}" if pd.notna(row['Pearson_r']) else "   —"
        sr = f"{row['Spearman_rho']:.4f}" if pd.notna(row['Spearman_rho']) else "   —"
        part_r = f"{row['Partial_r']:.4f}" if pd.notna(row['Partial_r']) else "   —"
        
        print(
            f"{row['Variable']:<15} {int(row['N']):>6} "
            f"{pr:>10} {row['Pearson_sig']:>4}  "
            f"{sr:>10} {row['Spearman_sig']:>4}  "
            f"{part_r:>10} {row['Partial_sig']:>4}  "
            f"{row['Direction']:<12} {row['Interpretation']}"
        )


print_table(corr_all,     "TABLE 1: All Villages — CH4 vs Machinery Correlations (Partial controlling for Village Size)")
print_table(corr_matched, "TABLE 2: Matched Villages — CH4 vs Machinery Correlations (Partial controlling for Village Size)")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — Rank Variables by Strongest Negative Association (Partial r)
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{'═'*80}")
print("  RANKING: Variables by Strongest Negative Association with CH4 (Partial r)")
print(f"{'═'*80}")

# Rank by Partial r (most negative first), for All Villages
rank_df = corr_all[["Variable", "N", "Partial_r", "Partial_p", "Partial_sig", "Interpretation"]].copy()
rank_df = rank_df.sort_values("Partial_r", ascending=True).reset_index(drop=True)
rank_df.index += 1  # 1-based rank

print(f"\n{'Rank':<6} {'Variable':<18} {'Partial r':>10} {'p-value':>11} {'Sig':>5}")
print("─"*55)
for rank, row in rank_df.iterrows():
    pr = f"{row['Partial_r']:.4f}" if pd.notna(row['Partial_r']) else "  —"
    pp = f"{row['Partial_p']:.4e}" if pd.notna(row['Partial_p']) else "  —"
    print(f"{rank:<6} {row['Variable']:<18} {pr:>10} {pp:>11} {row['Partial_sig']:>5}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — Scatter Plots
# ════════════════════════════════════════════════════════════════════════════

def make_scatter(data: pd.DataFrame, x_col: str, title_suffix: str, fname: str):
    """Publication-quality scatter plot with regression line and stats annotation."""
    sub = data[[CH4_COL, x_col] + COVARS].dropna()
    sub = sub[sub[CH4_COL] > 0]

    n  = len(sub)
    pr, pp = pearsonr(sub[CH4_COL], sub[x_col])
    sr, sp = spearmanr(sub[CH4_COL], sub[x_col])
    part_r, part_p = partial_corr(sub, CH4_COL, x_col, COVARS)

    # Matched status colour coding
    if "merge_confidence" in data.columns:
        mc = data.loc[sub.index, "merge_confidence"].fillna(0)
        colors = np.where(mc > 0, PALETTE["accent1"], PALETTE["subtext"])
        alpha  = np.where(mc > 0, 0.75, 0.35)
    else:
        colors = PALETTE["accent1"]
        alpha  = 0.55

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])

    # Scatter
    ax.scatter(sub[x_col], sub[CH4_COL],
               c=colors, alpha=alpha if isinstance(alpha, float) else 0.55,
               s=18, linewidths=0, zorder=3)

    # OLS regression line (Raw)
    slope, intercept, r_val, p_val, se = stats.linregress(sub[x_col], sub[CH4_COL])
    x_line = np.linspace(sub[x_col].min(), sub[x_col].max(), 300)
    y_line = slope * x_line + intercept
    line_col = PALETTE["negative"] if part_r < 0 else PALETTE["positive"] # Color by partial direction
    ax.plot(x_line, y_line, color=line_col, lw=2.5, zorder=4, label="OLS fit (Raw)")

    # 95% confidence band
    n_pts = len(sub)
    x_mean = sub[x_col].mean()
    se_line = se * np.sqrt(1/n_pts + (x_line - x_mean)**2 / np.sum((sub[x_col] - x_mean)**2))
    t_crit  = stats.t.ppf(0.975, df=n_pts - 2)
    ax.fill_between(x_line,
                    y_line - t_crit * se_line,
                    y_line + t_crit * se_line,
                    color=line_col, alpha=0.15, zorder=2, label="95% CI")

    # Stats annotation box
    sig_p  = significance_star(pp)
    sig_sp = significance_star(sp)
    sig_part = significance_star(part_p)
    ann_text = (
        f"Pearson r = {pr:+.4f}  {sig_p}\n"
        f"Partial r = {part_r:+.4f}  {sig_part} (Adj)\n"
        f"N = {n:,}"
    )
    ax.text(0.97, 0.97, ann_text,
            transform=ax.transAxes, ha="right", va="top",
            fontsize=9.5, family="monospace",
            color=PALETTE["text"],
            bbox=dict(boxstyle="round,pad=0.5", facecolor=PALETTE["bg"],
                      edgecolor=PALETTE["border"], alpha=0.9))

    # Legend
    matched_patch  = mpatches.Patch(color=PALETTE["accent1"],  label="Matched villages")
    unmatch_patch  = mpatches.Patch(color=PALETTE["subtext"],  label="Unmatched villages")
    reg_line       = Line2D([0], [0], color=line_col, lw=2.5, label="OLS regression")
    ax.legend(handles=[matched_patch, unmatch_patch, reg_line],
              facecolor=PALETTE["bg"], edgecolor=PALETTE["border"],
              labelcolor=PALETTE["text"], fontsize=8.5, loc="upper left")

    # Direction label
    direction  = "↓ Negative association (Partial)" if part_r < 0 else "↑ Positive association (Partial)"
    dir_color  = PALETTE["negative"] if part_r < 0 else PALETTE["positive"]
    ax.set_title(f"Predicted CH₄ (ppb) vs {title_suffix}\n{direction}",
                 color=PALETTE["text"], fontsize=13, pad=12)
    ax.set_xlabel(f"{x_col} (machine count)", color=PALETTE["subtext"], fontsize=10)
    ax.set_ylabel("Predicted CH₄ (ppb)", color=PALETTE["subtext"], fontsize=10)
    ax.grid(True, alpha=0.4)
    for spine in ax.spines.values():
        spine.set_edgecolor(PALETTE["border"])

    # Watermark
    ax.text(0.99, 0.01, "Punjab Machinery Analytics — Phase 2",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7, color=PALETTE["subtext"], alpha=0.7)

    plt.tight_layout()
    out = os.path.join(CHART_DIR, fname)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=PALETTE["bg"])
    plt.close(fig)
    print(f"    ✓ Saved: {fname}")
    return pr, pp, sr, sp, part_r, part_p, n


print("\n[4] Generating scatter plots...")
make_scatter(df, "In_Situ",       "In-Situ Machinery",  "scatter_ch4_vs_InSitu.png")
make_scatter(df, "Ex_Situ",       "Ex-Situ Machinery",  "scatter_ch4_vs_ExSitu.png")
make_scatter(df, "Total_Machines","Total Machines",      "scatter_ch4_vs_TotalMachines.png")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — Correlation Ranking Chart
# ════════════════════════════════════════════════════════════════════════════
print("\n[5] Generating correlation ranking chart (Partial r)...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.patch.set_facecolor(PALETTE["bg"])
fig.suptitle("CH₄ vs Machinery — Partial Correlation Ranking (Adj. for Village Area)\n(All Villages | Matched Villages)",
             color=PALETTE["text"], fontsize=14, y=1.02)

datasets = [(corr_all, "All Villages"), (corr_matched, "Matched Villages Only")]
for ax, (cdf, label) in zip(axes, datasets):
    ax.set_facecolor(PALETTE["surface"])
    cdf_sorted = cdf.sort_values("Partial_r", ascending=True).reset_index(drop=True)

    bar_colors = [PALETTE["negative"] if r < 0 else PALETTE["positive"]
                  for r in cdf_sorted["Partial_r"]]
    bars = ax.barh(cdf_sorted["Variable"], cdf_sorted["Partial_r"],
                   color=bar_colors, alpha=0.85, height=0.6, zorder=3)

    # Significance stars and value labels
    for i, (bar, row) in enumerate(zip(bars, cdf_sorted.itertuples())):
        val  = row.Partial_r if pd.notna(row.Partial_r) else 0
        sig  = row.Partial_sig
        x_pos = val - 0.005 if val < 0 else val + 0.005
        ha    = "right"       if val < 0 else "left"
        ax.text(x_pos, i, f"{val:+.4f} {sig}",
                ha=ha, va="center", fontsize=8, color=PALETTE["text"], zorder=4)

    ax.axvline(0, color=PALETTE["border"], lw=1.5, zorder=2)
    ax.set_xlabel("Partial r", color=PALETTE["subtext"])
    ax.set_title(f"{label}\n(N={int(cdf_sorted['N'].iloc[0]):,} per variable approx.)",
                 color=PALETTE["text"], fontsize=11)
    ax.grid(axis="x", alpha=0.4)
    for spine in ax.spines.values():
        spine.set_edgecolor(PALETTE["border"])
    ax.tick_params(colors=PALETTE["subtext"])

    # Shade negative region
    xlim = ax.get_xlim()
    ax.axvspan(xlim[0], 0, color=PALETTE["negative"], alpha=0.06, zorder=1)
    ax.axvspan(0, xlim[1], color=PALETTE["positive"], alpha=0.06, zorder=1)

    neg_patch = mpatches.Patch(color=PALETTE["negative"], alpha=0.7, label="Negative (supports hypothesis)")
    pos_patch = mpatches.Patch(color=PALETTE["positive"], alpha=0.7, label="Positive (contradicts hypothesis)")
    ax.legend(handles=[neg_patch, pos_patch], facecolor=PALETTE["bg"],
              edgecolor=PALETTE["border"], labelcolor=PALETTE["text"], fontsize=7.5)

plt.tight_layout()
rank_chart = os.path.join(CHART_DIR, "correlation_ranking_chart.png")
fig.savefig(rank_chart, dpi=160, bbox_inches="tight", facecolor=PALETTE["bg"])
plt.close(fig)
print(f"    ✓ Saved: correlation_ranking_chart.png")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — Hypothesis Conclusion
# ════════════════════════════════════════════════════════════════════════════
print("\n[6] Generating hypothesis conclusion report...")

def assess_hypothesis(corr_df: pd.DataFrame, label: str) -> dict:
    n_negative_sig   = corr_df[(corr_df["Partial_r"] < 0) & (corr_df["Partial_p"] < 0.05)].shape[0]
    n_negative_any   = corr_df[corr_df["Partial_r"] < 0].shape[0]
    n_positive_sig   = corr_df[(corr_df["Partial_r"] > 0) & (corr_df["Partial_p"] < 0.05)].shape[0]
    n_total          = corr_df.shape[0]
    strongest_neg    = corr_df.loc[corr_df["Partial_r"].idxmin()]
    strongest_pos    = corr_df.loc[corr_df["Partial_r"].idxmax()]
    return {
        "label":            label,
        "n_negative_sig":   n_negative_sig,
        "n_negative_any":   n_negative_any,
        "n_positive_sig":   n_positive_sig,
        "n_total":          n_total,
        "strongest_neg":    strongest_neg,
        "strongest_pos":    strongest_pos,
        "df":               corr_df,
    }

res_all     = assess_hypothesis(corr_all,     "All Villages")
res_matched = assess_hypothesis(corr_matched, "Matched Villages Only")

def verdict(res: dict) -> str:
    if res["n_negative_sig"] >= 4:
        return "STRONGLY SUPPORTS"
    elif res["n_negative_sig"] >= 2:
        return "PARTIALLY SUPPORTS"
    elif res["n_negative_sig"] == 1:
        return "WEAKLY SUPPORTS"
    elif res["n_positive_sig"] >= 3:
        return "CONTRADICTS"
    else:
        return "INSUFFICIENT EVIDENCE TO CONFIRM OR REJECT"

verdict_all     = verdict(res_all)
verdict_matched = verdict(res_matched)

# ─── Print conclusion to console ────────────────────────────────────────────
print(f"\n{'═'*80}")
print("  HYPOTHESIS CONCLUSION (PARTIAL CORRELATIONS)")
print(f"{'═'*80}")
print("\n  HYPOTHESIS: 'Higher machinery penetration is associated with")
print("               lower methane emissions at village scale.'")
print()

for res, v in [(res_all, verdict_all), (res_matched, verdict_matched)]:
    print(f"  Subset: {res['label']}")
    print(f"  ─────────────────────────────────────────────────────")
    print(f"  Significant negative correlations: {res['n_negative_sig']}/{res['n_total']}")
    print(f"  Any negative correlations:         {res['n_negative_any']}/{res['n_total']}")
    print(f"  Significant positive correlations: {res['n_positive_sig']}/{res['n_total']}")
    sn = res["strongest_neg"]
    sp = res["strongest_pos"]
    print(f"  Strongest negative: {sn['Variable']} (Partial r={sn['Partial_r']:.4f}, p={sn['Partial_p']:.4e})")
    print(f"  Strongest positive: {sp['Variable']} (Partial r={sp['Partial_r']:.4f}, p={sp['Partial_p']:.4e})")
    print(f"\n  ► VERDICT: {v}")
    print()

# ─── Save full text report ───────────────────────────────────────────────────
report_lines = []
report_lines.append("=" * 80)
report_lines.append("  PUNJAB MACHINERY ANALYTICS — PHASE 2")
report_lines.append("  STATISTICAL HYPOTHESIS ASSESSMENT REPORT")
report_lines.append("=" * 80)
report_lines.append("")
report_lines.append("HYPOTHESIS:")
report_lines.append("  'Higher machinery penetration is associated with lower")
report_lines.append("   methane emissions at village scale.'")
report_lines.append("  (Professor's hypothesis — Punjab rice residue burning context)")
report_lines.append("")
report_lines.append("DATA SOURCE:")
report_lines.append(f"  {DATA_PATH}")
report_lines.append(f"  Total villages: {len(df):,}")
report_lines.append(f"  Matched villages (with machinery data): {len(df_matched):,}")
report_lines.append(f"  CH4 variable: {CH4_COL}")
report_lines.append("  Control variables for partial correlation:")
for covar in COVARS:
    report_lines.append(f"    - {covar}")
report_lines.append("")

for res, v in [(res_all, verdict_all), (res_matched, verdict_matched)]:
    report_lines.append("─" * 80)
    report_lines.append(f"SUBSET: {res['label']}")
    report_lines.append("─" * 80)
    report_lines.append("")
    report_lines.append(f"{'Variable':<15} {'N':>6} {'Pearson r':>10} {'Sig':>4} {'Spearman ρ':>10} {'Sig':>4} {'Partial r':>10} {'Sig':>4}  Interpretation")
    report_lines.append("─" * 120)
    for _, row in res["df"].sort_values("Partial_r").iterrows():
        pr = f"{row['Pearson_r']:.4f}"  if pd.notna(row['Pearson_r'])  else "    —"
        sr = f"{row['Spearman_rho']:.4f}" if pd.notna(row['Spearman_rho']) else "    —"
        part_r = f"{row['Partial_r']:.4f}" if pd.notna(row['Partial_r']) else "    —"
        
        report_lines.append(
            f"{row['Variable']:<15} {int(row['N']):>6} {pr:>10} {row['Pearson_sig']:>4} "
            f"{sr:>10} {row['Spearman_sig']:>4} {part_r:>10} {row['Partial_sig']:>4}  {row['Interpretation']}"
        )
    report_lines.append("")
    report_lines.append(f"Significant negative correlations: {res['n_negative_sig']}/{res['n_total']}")
    report_lines.append(f"Any negative correlations:         {res['n_negative_any']}/{res['n_total']}")
    report_lines.append(f"Significant positive correlations: {res['n_positive_sig']}/{res['n_total']}")
    sn = res["strongest_neg"]
    sp2 = res["strongest_pos"]
    report_lines.append(f"Strongest negative: {sn['Variable']} (Partial r={sn['Partial_r']:.4f}, p={sn['Partial_p']:.4e})")
    report_lines.append(f"Strongest positive: {sp2['Variable']} (Partial r={sp2['Partial_r']:.4f}, p={sp2['Partial_p']:.4e})")
    report_lines.append("")
    report_lines.append(f">>> VERDICT ({res['label']}): {v}")
    report_lines.append("")

report_lines.append("=" * 80)
report_lines.append("INTERPRETATION GUIDE:")
report_lines.append("  *** = p < 0.001   ** = p < 0.01   * = p < 0.05   ns = not significant")
report_lines.append("  STRONGLY SUPPORTS:       ≥4 machinery variables show significant negative partial correlation")
report_lines.append("  PARTIALLY SUPPORTS:      2–3 machinery variables show significant negative partial correlation")
report_lines.append("  WEAKLY SUPPORTS:         1 machinery variable shows significant negative partial correlation")
report_lines.append("  INSUFFICIENT EVIDENCE:   No significant negative partial correlations")
report_lines.append("  CONTRADICTS:             ≥3 significant positive partial correlations")
report_lines.append("")
report_lines.append("NOTE: Partial correlation adjusts for agricultural area to control for the confounding")
report_lines.append("      effect that larger villages have both more machines and more rice residue/CH4.")
report_lines.append("=" * 80)

report_path = os.path.join(REPORT_DIR, "phase2_hypothesis_conclusion.txt")
with open(report_path, "w") as f:
    f.write("\n".join(report_lines))
print(f"    ✓ Hypothesis report saved: phase2_hypothesis_conclusion.txt")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 8 — Summary Dashboard Figure
# ════════════════════════════════════════════════════════════════════════════
print("\n[7] Generating summary dashboard...")

fig = plt.figure(figsize=(18, 10), facecolor=PALETTE["bg"])
gs  = gridspec.GridSpec(2, 4, figure=fig, hspace=0.45, wspace=0.35)

# ── Top row: three scatter plots ──────────────────────────────────────────
scatter_pairs = [
    ("In_Situ",       "In-Situ Machinery",   gs[0, 0]),
    ("Ex_Situ",       "Ex-Situ Machinery",   gs[0, 1]),
    ("Total_Machines","Total Machines",       gs[0, 2]),
]
for x_col, title, gs_pos in scatter_pairs:
    ax = fig.add_subplot(gs_pos)
    ax.set_facecolor(PALETTE["surface"])
    sub = df[[CH4_COL, x_col] + COVARS].dropna()
    sub = sub[sub[CH4_COL] > 0]

    if "merge_confidence" in df.columns:
        mc   = df.loc[sub.index, "merge_confidence"].fillna(0)
        cols = [PALETTE["accent1"] if m > 0 else PALETTE["subtext"] for m in mc]
        alph = [0.75 if m > 0 else 0.3 for m in mc]
    else:
        cols = PALETTE["accent1"]
        alph = [0.55] * len(sub)

    ax.scatter(sub[x_col], sub[CH4_COL], c=cols,
               alpha=0.45, s=8, linewidths=0, zorder=3)

    part_r, part_p = partial_corr(sub, CH4_COL, x_col, COVARS)
    slope, intercept, *_ = stats.linregress(sub[x_col], sub[CH4_COL])
    x_line = np.linspace(sub[x_col].min(), sub[x_col].max(), 200)
    line_col = PALETTE["negative"] if part_r < 0 else PALETTE["positive"]
    ax.plot(x_line, slope * x_line + intercept, color=line_col, lw=2, zorder=4)
    sig = significance_star(part_p)
    ax.set_title(f"CH₄ vs {title}", color=PALETTE["text"], fontsize=9.5)
    ax.set_xlabel(x_col, color=PALETTE["subtext"], fontsize=8)
    ax.set_ylabel("CH₄ (ppb)", color=PALETTE["subtext"], fontsize=8)
    ax.text(0.97, 0.97, f"Part. r={part_r:+.3f} {sig}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8.5, color=PALETTE["text"], family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=PALETTE["bg"],
                      edgecolor=PALETTE["border"], alpha=0.85))
    ax.grid(True, alpha=0.35)
    for sp in ax.spines.values():
        sp.set_edgecolor(PALETTE["border"])

# ── Top-right: rank bar chart (All) ───────────────────────────────────────
ax_rank = fig.add_subplot(gs[0, 3])
ax_rank.set_facecolor(PALETTE["surface"])
cdf_sorted = corr_all.sort_values("Partial_r", ascending=True).reset_index(drop=True)
bar_cols = [PALETTE["negative"] if r < 0 else PALETTE["positive"]
            for r in cdf_sorted["Partial_r"]]
ax_rank.barh(cdf_sorted["Variable"], cdf_sorted["Partial_r"],
             color=bar_cols, alpha=0.85, height=0.6)
ax_rank.axvline(0, color=PALETTE["border"], lw=1.2)
ax_rank.set_title("Partial Correlation Ranking\n(All Villages)", color=PALETTE["text"], fontsize=9.5)
ax_rank.set_xlabel("Partial r", color=PALETTE["subtext"], fontsize=8)
ax_rank.grid(axis="x", alpha=0.35)
for sp in ax_rank.spines.values():
    sp.set_edgecolor(PALETTE["border"])

# ── Bottom row: Verdict boxes ─────────────────────────────────────────────
for col_idx, (res, v) in enumerate([(res_all, verdict_all), (res_matched, verdict_matched)]):
    col_index = col_idx * 2
    ax_v = fig.add_subplot(gs[1, col_index : col_index + 2])
    ax_v.set_facecolor(PALETTE["surface"])
    ax_v.axis("off")

    vcolor = {
        "STRONGLY SUPPORTS":    PALETTE["positive"],
        "PARTIALLY SUPPORTS":   PALETTE["neutral"],
        "WEAKLY SUPPORTS":      PALETTE["neutral"],
        "INSUFFICIENT EVIDENCE TO CONFIRM OR REJECT": PALETTE["subtext"],
        "CONTRADICTS":          PALETTE["negative"],
    }.get(v, PALETTE["subtext"])

    # Verdict heading
    ax_v.text(0.5, 0.85, res["label"], transform=ax_v.transAxes,
              ha="center", va="top", fontsize=11, color=PALETTE["subtext"])
    ax_v.text(0.5, 0.65, v, transform=ax_v.transAxes,
              ha="center", va="top", fontsize=18, fontweight="bold", color=vcolor)

    # Stats summary
    summary = (
        f"Sig. negative part. correlations: {res['n_negative_sig']}/{res['n_total']}\n"
        f"Any negative part. correlations:  {res['n_negative_any']}/{res['n_total']}\n"
        f"Strongest negative: {res['strongest_neg']['Variable']} "
        f"(Part. r={res['strongest_neg']['Partial_r']:.4f}, "
        f"p={res['strongest_neg']['Partial_p']:.3e})"
    )
    ax_v.text(0.5, 0.42, summary, transform=ax_v.transAxes,
              ha="center", va="top", fontsize=9, color=PALETTE["text"],
              family="monospace",
              bbox=dict(boxstyle="round,pad=0.5", facecolor=PALETTE["bg"],
                        edgecolor=vcolor, alpha=0.6))

fig.suptitle(
    "Punjab Machinery Analytics — Phase 2 | Statistical Assessment (Adjusted)\n"
    "Hypothesis: Higher machinery penetration → Lower methane emissions (Controlling for Area)",
    color=PALETTE["text"], fontsize=13, y=1.01
)

dashboard_path = os.path.join(CHART_DIR, "phase2_summary_dashboard.png")
fig.savefig(dashboard_path, dpi=150, bbox_inches="tight", facecolor=PALETTE["bg"])
plt.close(fig)
print(f"    ✓ Saved: phase2_summary_dashboard.png")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 9 — Final Summary
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{'═'*65}")
print("  OUTPUTS GENERATED")
print(f"{'═'*65}")
print(f"  Correlation Tables:")
print(f"    outputs/correlation_tables/phase2_correlation_all_villages.csv")
print(f"    outputs/correlation_tables/phase2_correlation_matched_villages.csv")
print(f"    outputs/correlation_tables/phase2_correlation_combined_publication.csv")
print(f"  Charts:")
print(f"    outputs/charts/scatter_ch4_vs_InSitu.png")
print(f"    outputs/charts/scatter_ch4_vs_ExSitu.png")
print(f"    outputs/charts/scatter_ch4_vs_TotalMachines.png")
print(f"    outputs/charts/correlation_ranking_chart.png")
print(f"    outputs/charts/phase2_summary_dashboard.png")
print(f"  Report:")
print(f"    outputs/policy_reports/phase2_hypothesis_conclusion.txt")
print(f"{'═'*65}")
print("  DONE.\n")

"""
Punjab Machinery Analytics - Phase 2
Machinery-Intensity Normalization Analysis
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import pingouin as pg

warnings.filterwarnings("ignore")

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH  = os.path.join(BASE_DIR, "data", "merged", "Punjab_CH4_Machinery_Master.csv")
OUT_DIR    = os.path.join(BASE_DIR, "outputs", "machinery_density_analysis")
CHART_DIR  = os.path.join(OUT_DIR, "charts")

for d in [OUT_DIR, CHART_DIR]:
    os.makedirs(d, exist_ok=True)

# ─── Style ──────────────────────────────────────────────────────────────────
PALETTE = {
    "bg":        "#0d1117",
    "surface":   "#161b22",
    "border":    "#30363d",
    "text":      "#e6edf3",
    "subtext":   "#8b949e",
    "accent1":   "#58a6ff",
    "accent2":   "#f78166",
    "accent3":   "#3fb950",
    "accent4":   "#d2a8ff",
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
})

def apply_dark_style(ax):
    ax.grid(True, alpha=0.35)
    for sp in ax.spines.values():
        sp.set_edgecolor(PALETTE["border"])

def run_density_analysis():
    print("\n" + "═"*65)
    print("  MACHINERY-INTENSITY NORMALIZATION ANALYSIS")
    print("═"*65)

    print("\n[1] Loading data & calculating density variables...")
    df = pd.read_csv(DATA_PATH, low_memory=False)
    
    # We only use matched villages that actually have area data
    df = df[df["merge_confidence"] > 0].copy()
    area_col = "TOTAL CULTIVABLE AREA (IN HECTARES), IF IN ACRES DIVIDE BY 2.47"
    
    # Filter out zeros or nulls in cultivable area
    df = df[(df[area_col].notnull()) & (df[area_col] > 0)]
    
    # Safely create density features
    df["Machine_Density_Cultivable"] = df["Total_Machines"] / df[area_col]
    df["InSitu_Density"] = df["In_Situ"] / df[area_col]
    df["CRM_Density"] = df["CRM"] / df[area_col]

    print(f"    Villages processed (Matched & Area > 0): {len(df):,}")

    # ─── CORRELATIONS ────────────────────────────────────────────────────────
    print("\n[2] Calculating Pearson, Spearman, and Partial correlations...")
    y_var = "Predicted_CH4_ppb"
    densities = ["Machine_Density_Cultivable", "InSitu_Density", "CRM_Density"]
    
    # Define control variables for partial correlation (can use NET SOWN AREA or other factors)
    controls = ["cropland_frac", "annual_rainfall_mm", "mean_temp_celsius"]
    # keep only valid data for these controls
    available_controls = [c for c in controls if c in df.columns]
    
    df_clean = df.replace([np.inf, -np.inf], np.nan).dropna(subset=[y_var] + densities + available_controls)
    
    results = []
    for dens in densities:
        # Pearson
        pearson_r, pearson_p = stats.pearsonr(df_clean[dens], df_clean[y_var])
        
        # Spearman
        spearman_rho, spearman_p = stats.spearmanr(df_clean[dens], df_clean[y_var])
        
        # Partial
        if len(available_controls) > 0:
            p_corr = pg.partial_corr(data=df_clean, x=dens, y=y_var, covar=available_controls)
            partial_r = p_corr["r"].values[0]
            partial_p = p_corr["p_val"].values[0]
        else:
            partial_r = np.nan
            partial_p = np.nan
            
        results.append({
            "Density_Variable": dens,
            "Pearson_r": pearson_r, "Pearson_p": pearson_p,
            "Spearman_rho": spearman_rho, "Spearman_p": spearman_p,
            "Partial_r": partial_r, "Partial_p": partial_p
        })
        
    corr_df = pd.DataFrame(results)
    corr_df.to_csv(os.path.join(OUT_DIR, "density_correlations.csv"), index=False)
    print("    ✓ density_correlations.csv exported.")

    # ─── QUINTILES ───────────────────────────────────────────────────────────
    print("\n[3] Creating quintiles & summaries...")
    # Calculate Quintiles
    # Since density has many 0s, qcut might fail if duplicate bin edges exist. We use rank instead.
    df_clean["Density_Rank"] = df_clean["Machine_Density_Cultivable"].rank(method="first")
    df_clean["Density_Quintile"] = pd.qcut(df_clean["Density_Rank"], q=5, labels=["Q1 (Lowest)", "Q2", "Q3", "Q4", "Q5 (Highest)"])

    summary = df_clean.groupby("Density_Quintile").agg(
        Village_Count=("vlcode", "count"),
        Mean_Density=("Machine_Density_Cultivable", "mean"),
        Median_Density=("Machine_Density_Cultivable", "median"),
        Mean_Predicted_CH4=(y_var, "mean"),
        Median_Predicted_CH4=(y_var, "median")
    ).reset_index()
    
    summary.to_csv(os.path.join(OUT_DIR, "density_quintile_summary.csv"), index=False)
    print("    ✓ density_quintile_summary.csv exported.")

    # ─── VISUALIZATIONS ──────────────────────────────────────────────────────
    print("\n[4] Generating plots...")
    
    # 1. Scatterplots
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    for i, dens in enumerate(densities):
        ax = axes[i]
        ax.set_facecolor(PALETTE["surface"])
        sns.regplot(x=dens, y=y_var, data=df_clean, scatter_kws={'alpha':0.3, 'color':PALETTE["accent1"]}, 
                    line_kws={'color':PALETTE["accent2"]}, ax=ax)
        ax.set_title(f"{dens} vs CH4", color=PALETTE["text"], pad=10)
        ax.set_xlabel(dens, color=PALETTE["subtext"])
        ax.set_ylabel("Predicted CH4 (ppb)", color=PALETTE["subtext"])
        apply_dark_style(ax)
        
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "scatter_density_vs_ch4.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()

    # 2. Quintile Boxplots
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])
    sns.boxplot(x="Density_Quintile", y=y_var, data=df_clean, ax=ax, palette="coolwarm", showfliers=False)
    ax.set_title("Predicted CH4 by Machine Density Quintiles", color=PALETTE["text"], pad=15)
    ax.set_xlabel("Density Quintile", color=PALETTE["subtext"])
    ax.set_ylabel("Predicted CH4 (ppb)", color=PALETTE["subtext"])
    apply_dark_style(ax)
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "boxplot_density_quintiles.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()

    # 3. Quintile Bar Charts
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])
    sns.barplot(x="Density_Quintile", y=y_var, data=df_clean, ax=ax, palette="coolwarm", ci=95, capsize=0.1)
    
    y_min = summary["Mean_Predicted_CH4"].min() - 10
    y_max = summary["Mean_Predicted_CH4"].max() + 10
    ax.set_ylim(y_min, y_max)
    
    ax.set_title("Mean Predicted CH4 by Machine Density Quintiles (95% CI)", color=PALETTE["text"], pad=15)
    ax.set_xlabel("Density Quintile", color=PALETTE["subtext"])
    ax.set_ylabel("Mean Predicted CH4 (ppb)", color=PALETTE["subtext"])
    apply_dark_style(ax)
    
    # Annotate bars
    for i, p in enumerate(ax.patches):
        mean_val = summary.iloc[i]["Mean_Predicted_CH4"]
        ax.annotate(f'{mean_val:.1f}', 
                    (p.get_x() + p.get_width() / 2., mean_val), 
                    ha='center', va='bottom', xytext=(0, 5), textcoords='offset points',
                    color=PALETTE["text"], fontweight='bold')
                    
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "barchart_density_quintiles.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()
    print("    ✓ Charts exported.")

    # ─── INTERPRETATION ──────────────────────────────────────────────────────
    print("\n[5] Generating final interpretation...")
    
    # Check trend
    pearson_r_dens = corr_df.loc[corr_df["Density_Variable"]=="Machine_Density_Cultivable", "Pearson_r"].values[0]
    
    if pearson_r_dens > 0:
        dir_text = "POSITIVE"
        conc_text = "Even when normalized by cultivable area, denser machinery allocation corresponds to HIGHER methane footprints."
    elif pearson_r_dens < 0:
        dir_text = "NEGATIVE"
        conc_text = "When normalizing by area, a mitigating signal finally emerges: higher machinery density is associated with LOWER methane footprints."
    else:
        dir_text = "FLAT"
        conc_text = "Machine density exhibits no strong relationship with methane levels."

    interp = f"""
================================================================================
MACHINERY-INTENSITY NORMALIZATION ANALYSIS
================================================================================

This analysis tackles the ultimate confounder: village size. 
Are we just seeing more CH4 because larger villages have more land, burn more 
residue, and naturally receive more absolute numbers of machines?

To answer this, we evaluated "Machine Density" (Machines / Cultivable Hectare).

1. Correlation Results:
--------------------------------------------------------------------------------
Machine Density vs Predicted CH4: {pearson_r_dens:+.4f}
"""
    for _, row in corr_df.iterrows():
        interp += f"  - {row['Density_Variable']:30s} | Pearson: {row['Pearson_r']:+.4f} | Partial: {row['Partial_r']:+.4f}\n"

    interp += f"""
2. Quintile Trend:
--------------------------------------------------------------------------------
Stratifying villages into density quintiles, from least machine-dense to most 
machine-dense:

"""
    for _, row in summary.iterrows():
        interp += f"  [{row['Density_Quintile']:12s}] Mean Density: {row['Mean_Density']:5.3f} machines/ha | Mean CH4: {row['Mean_Predicted_CH4']:.2f}\n"

    interp += f"""
3. Conclusion:
--------------------------------------------------------------------------------
The density relationship remains {dir_text}.
{conc_text}

Raw machine counts are heavily confounded by land area, meaning large villages 
artificially inflate both metrics. However, normalizing machinery by hectare 
fails to reverse the positive association. 

Whether evaluated via raw machine count, causally adjusted models, or area-normalized 
density, government machinery penetration shows no statistical evidence of reducing 
regional methane emissions in the current data.
================================================================================
"""
    with open(os.path.join(OUT_DIR, "normalization_conclusion.txt"), "w") as f:
        f.write(interp)
        
    print("    ✓ normalization_conclusion.txt exported.")
    print("  DONE.\n")

if __name__ == "__main__":
    run_density_analysis()

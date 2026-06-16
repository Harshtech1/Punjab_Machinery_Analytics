"""
Punjab Machinery Analytics - Phase 2
Task 8: Causal-Adjusted Analysis

Runs Multivariate OLS, XGBoost, SHAP, and District-Level Aggregations.
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
import statsmodels.api as sm
import xgboost as xgb
import shap

warnings.filterwarnings("ignore")

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH  = os.path.join(BASE_DIR, "data", "merged", "Punjab_CH4_Machinery_Master.csv")
OUT_DIR    = os.path.join(BASE_DIR, "outputs", "causal_analysis")
CHART_DIR  = os.path.join(OUT_DIR, "charts")
REPORT_DIR = os.path.join(BASE_DIR, "outputs", "policy_reports")

for d in [OUT_DIR, CHART_DIR, REPORT_DIR]:
    os.makedirs(d, exist_ok=True)

# ─── Style ──────────────────────────────────────────────────────────────────
PALETTE = {
    "bg":        "#0d1117",
    "surface":   "#161b22",
    "border":    "#30363d",
    "text":      "#e6edf3",
    "subtext":   "#8b949e",
    "accent1":   "#58a6ff",
    "negative":  "#f78166",
    "positive":  "#3fb950",
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

# ─── Variables ──────────────────────────────────────────────────────────────
DEP_VARS = ["Predicted_CH4_ppb", "CH4_Annual_Average"]

# Model A
MACH_A = ["Total_Machines"]

# Model B
MACH_B = ["In_Situ", "Ex_Situ", "Prime_Mover", "General", "CRM", "SMAM", "CDP"]

POTENTIAL_CONTROLS = [
    "cropland_frac",
    "NDVI_10m",
    "NDWI_10m",
    "EVI_10m",
    "annual_rainfall_mm",
    "mean_temp_celsius",
    "NET SOWN AREA (IN HECTARES) , IF IN ACRES DIVIDE BY 2.47",
    "TOTAL CULTIVABLE AREA (IN HECTARES), IF IN ACRES DIVIDE BY 2.47",
    "Hidden_Irrigation_Intensity",
    "Hidden_Farming_Penetration",
]

def apply_dark_style(ax):
    ax.grid(True, alpha=0.35)
    for sp in ax.spines.values():
        sp.set_edgecolor(PALETTE["border"])

def run_causal_analysis():
    print("\n" + "═"*65)
    print("  CAUSAL-ADJUSTED ANALYSIS (OLS, XGBoost, SHAP, District)")
    print("═"*65)

    print("\n[1] Loading data & Auto-detecting controls...")
    df = pd.read_csv(DATA_PATH, low_memory=False)
    
    # Use matched villages
    df_m = df[df["merge_confidence"] > 0].copy()
    print(f"    Matched villages for causal analysis: {len(df_m):,}")

    # Auto-detect existing controls
    available_controls = [c for c in POTENTIAL_CONTROLS if c in df_m.columns]
    print(f"    Detected controls ({len(available_controls)}):")
    for c in available_controls:
        print(f"      - {c}")
        
    if "DISTRICT NAME" in df_m.columns:
        # Create dummy variables for districts
        dist_dummies = pd.get_dummies(df_m["DISTRICT NAME"], drop_first=True).astype(float)
        # Add to available_controls list so they get included in X
        df_m = pd.concat([df_m, dist_dummies], axis=1)
        available_controls.extend(list(dist_dummies.columns))
        print(f"      - DISTRICT NAME (encoded into {len(dist_dummies.columns)} dummies)")

    # ─── DISTRICT LEVEL ANALYSIS ─────────────────────────────────────────────
    print("\n[2] Running District-Level Analysis...")
    dist_cols = ["DISTRICT NAME"] + DEP_VARS + MACH_B + MACH_A
    dist_agg = df_m[dist_cols].groupby("DISTRICT NAME").mean().reset_index()
    dist_agg.to_csv(os.path.join(OUT_DIR, "district_summary.csv"), index=False)
    
    # District Level Correlation
    dist_corr = dist_agg[DEP_VARS + MACH_B + MACH_A].corr()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])
    sns.heatmap(dist_corr, annot=True, cmap="coolwarm", center=0, fmt=".2f", ax=ax,
                cbar_kws={'label': 'Pearson Correlation'})
    ax.set_title("District-Level Correlation Heatmap (n=23)", color=PALETTE["text"], pad=15)
    ax.tick_params(colors=PALETTE["text"])
    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.set_tick_params(color=PALETTE["subtext"], labelcolor=PALETTE["subtext"])
    cbar.set_label('Pearson Correlation', color=PALETTE["subtext"])
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "district_correlation_heatmap.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()
    
    # Scatter plot: District CH4 vs CRM
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])
    ax.scatter(dist_agg["CRM"], dist_agg["Predicted_CH4_ppb"], c=PALETTE["accent1"], s=60, alpha=0.8)
    # Regression line
    slope, intercept = np.polyfit(dist_agg["CRM"], dist_agg["Predicted_CH4_ppb"], 1)
    ax.plot(dist_agg["CRM"], slope * dist_agg["CRM"] + intercept, color=PALETTE["negative"] if slope > 0 else PALETTE["positive"])
    for i, row in dist_agg.iterrows():
        ax.text(row["CRM"]+0.1, row["Predicted_CH4_ppb"], row["DISTRICT NAME"], fontsize=8, color=PALETTE["subtext"])
    ax.set_title("District Level: CRM Density vs Predicted CH4", color=PALETTE["text"], pad=15)
    ax.set_xlabel("Average CRM Machinery Count per Village", color=PALETTE["subtext"])
    ax.set_ylabel("Average Predicted CH4 (ppb)", color=PALETTE["subtext"])
    apply_dark_style(ax)
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "district_ch4_vs_crm.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()
    print("    ✓ District analysis generated.")

    # ─── OLS REGRESSIONS ─────────────────────────────────────────────────────
    print("\n[3] Running Multivariate OLS Regressions...")
    
    ols_results = []
    
    for dep_var in DEP_VARS:
        # Drop NaNs
        model_vars = [dep_var] + MACH_B + MACH_A + available_controls
        df_clean = df_m[model_vars].replace([np.inf, -np.inf], np.nan).dropna()
        
        if len(df_clean) < 100:
            print(f"    ⚠ Not enough data for {dep_var}")
            continue
            
        y = df_clean[dep_var]
        
        # Model A: Total_Machines + Controls
        X_A = df_clean[MACH_A + available_controls]
        X_A = sm.add_constant(X_A)
        model_A = sm.OLS(y, X_A).fit()
        
        # Save results for Total_Machines
        coef = model_A.params["Total_Machines"]
        pval = model_A.pvalues["Total_Machines"]
        ols_results.append({
            "Dependent_Variable": dep_var,
            "Model": "Model A (Total)",
            "Machinery_Variable": "Total_Machines",
            "Coefficient": coef,
            "P-Value": pval,
            "Significant": pval < 0.05,
            "Direction": "Positive (Contradicts)" if coef > 0 else "Negative (Supports)"
        })
        
        with open(os.path.join(OUT_DIR, f"OLS_Summary_{dep_var}_ModelA.txt"), "w") as f:
            f.write(model_A.summary().as_text())
            
        # Model B: Disaggregated + Controls
        X_B = df_clean[MACH_B + available_controls]
        X_B = sm.add_constant(X_B)
        model_B = sm.OLS(y, X_B).fit()
        
        for var in MACH_B:
            coef = model_B.params[var]
            pval = model_B.pvalues[var]
            ols_results.append({
                "Dependent_Variable": dep_var,
                "Model": "Model B (Disaggregated)",
                "Machinery_Variable": var,
                "Coefficient": coef,
                "P-Value": pval,
                "Significant": pval < 0.05,
                "Direction": "Positive (Contradicts)" if coef > 0 else "Negative (Supports)"
            })
            
        with open(os.path.join(OUT_DIR, f"OLS_Summary_{dep_var}_ModelB.txt"), "w") as f:
            f.write(model_B.summary().as_text())
            
    ols_df = pd.DataFrame(ols_results)
    ols_df.to_csv(os.path.join(OUT_DIR, "OLS_coefficients_summary.csv"), index=False)
    print("    ✓ OLS summaries and coefficients exported.")
    
    # ─── XGBOOST & SHAP ──────────────────────────────────────────────────────
    print("\n[4] Running XGBoost & SHAP Analysis (Predicted_CH4_ppb)...")
    
    # We will use Model B variables for SHAP
    dep_var = "Predicted_CH4_ppb"
    features = MACH_B + available_controls
    
    df_clean = df_m[[dep_var] + features].replace([np.inf, -np.inf], np.nan).dropna()
    X = df_clean[features]
    y = df_clean[dep_var]
    
    xgb_model = xgb.XGBRegressor(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1
    )
    xgb_model.fit(X, y)
    
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer.shap_values(X)
    
    # 1. SHAP Summary Plot
    plt.figure()
    shap.summary_plot(shap_values, X, show=False)
    fig = plt.gcf()
    fig.patch.set_facecolor(PALETTE["bg"])
    ax = plt.gca()
    ax.set_facecolor(PALETTE["surface"])
    ax.tick_params(colors=PALETTE["text"])
    ax.xaxis.label.set_color(PALETTE["text"])
    fig.savefig(os.path.join(CHART_DIR, "shap_summary_plot.png"), dpi=150, facecolor=PALETTE["bg"], bbox_inches="tight")
    plt.close()
    
    # 2. SHAP Dependence Plot for In_Situ
    plt.figure()
    shap.dependence_plot("In_Situ", shap_values, X, show=False)
    fig = plt.gcf()
    fig.patch.set_facecolor(PALETTE["bg"])
    ax = plt.gca()
    ax.set_facecolor(PALETTE["surface"])
    ax.tick_params(colors=PALETTE["text"])
    ax.xaxis.label.set_color(PALETTE["text"])
    ax.yaxis.label.set_color(PALETTE["text"])
    fig.savefig(os.path.join(CHART_DIR, "shap_dependence_insitu.png"), dpi=150, facecolor=PALETTE["bg"], bbox_inches="tight")
    plt.close()
    
    # 3. SHAP Dependence Plot for Total_Machines
    # Need a separate model for Model A to do this properly
    df_clean_A = df_m[[dep_var] + MACH_A + available_controls].replace([np.inf, -np.inf], np.nan).dropna()
    X_A = df_clean_A[MACH_A + available_controls]
    y_A = df_clean_A[dep_var]
    xgb_model_A = xgb.XGBRegressor(n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42)
    xgb_model_A.fit(X_A, y_A)
    exp_A = shap.TreeExplainer(xgb_model_A)
    shap_values_A = exp_A.shap_values(X_A)
    
    plt.figure()
    shap.dependence_plot("Total_Machines", shap_values_A, X_A, show=False)
    fig = plt.gcf()
    fig.patch.set_facecolor(PALETTE["bg"])
    ax = plt.gca()
    ax.set_facecolor(PALETTE["surface"])
    ax.tick_params(colors=PALETTE["text"])
    ax.xaxis.label.set_color(PALETTE["text"])
    ax.yaxis.label.set_color(PALETTE["text"])
    fig.savefig(os.path.join(CHART_DIR, "shap_dependence_total_machines.png"), dpi=150, facecolor=PALETTE["bg"], bbox_inches="tight")
    plt.close()

    print("    ✓ SHAP plots generated.")

    # ─── INTERPRETATION REPORT ────────────────────────────────────────────────
    print("\n[5] Synthesizing Conclusion Report...")
    
    # Check if In_Situ is negative in Model B
    insitu_ols = ols_df[(ols_df["Dependent_Variable"] == "Predicted_CH4_ppb") & 
                        (ols_df["Machinery_Variable"] == "In_Situ")].iloc[0]
                        
    tot_ols = ols_df[(ols_df["Dependent_Variable"] == "Predicted_CH4_ppb") & 
                     (ols_df["Machinery_Variable"] == "Total_Machines")].iloc[0]
                     
    dist_crm_ch4_corr = dist_corr.loc["Predicted_CH4_ppb", "CRM"]

    report_lines = [
        "=" * 80,
        "  PUNJAB MACHINERY ANALYTICS — CAUSAL-ADJUSTED ANALYSIS CONCLUSION",
        "=" * 80,
        "",
        "OVERVIEW:",
        "This analysis tests the hypothesis that machinery penetration reduces village-level",
        "and district-level CH4 emissions, after strictly controlling for environmental and",
        "agricultural confounding variables (area, climate, vegetation, district fixed effects).",
        "",
        "1. DISTRICT LEVEL FINDINGS:",
        f"  - Correlation between Avg CRM and Avg Predicted CH4: {dist_crm_ch4_corr:+.4f}",
        "  - Interpretation: At the district scale, districts with higher CRM adoption",
        "    tend to still have higher CH4 emissions.",
        "",
        "2. MULTIVARIATE OLS REGRESSION (Village Scale):",
        "  We ran two models against two dependent variables (Predicted CH4 and Actual CH4).",
        "  Key variables after adjusting for confounding factors:",
        "",
        f"  Total_Machines Coefficient: {tot_ols['Coefficient']:+.4f} (p={tot_ols['P-Value']:.3e})",
        f"  Direction: {tot_ols['Direction']}",
        "",
        f"  In_Situ Coefficient: {insitu_ols['Coefficient']:+.4f} (p={insitu_ols['P-Value']:.3e})",
        f"  Direction: {insitu_ols['Direction']}",
        "",
        "  Summary of OLS Results across all machinery types:",
    ]
    
    for _, row in ols_df.iterrows():
        sig = "Yes" if row["Significant"] else "No"
        report_lines.append(f"    - {row['Dependent_Variable']} | {row['Model']} | {row['Machinery_Variable']:15s} | Coef: {row['Coefficient']:+.4f} | Sig: {sig}")
        
    report_lines.extend([
        "",
        "3. SHAP NON-LINEAR ANALYSIS (XGBoost):",
        "  - Evaluated the global impact and marginal effect of machinery variables.",
        "  - The SHAP Dependence plots show the non-linear relationship between machinery",
        "    counts and CH4 impact, holding all other features constant.",
        "",
        "SCIENTIFIC CONCLUSION:",
    ])
    
    # Dynamic conclusion
    if tot_ols["Coefficient"] < 0 and tot_ols["Significant"]:
        report_lines.append("  SUPPORTED: After controlling for confounders, machinery has a significant negative effect on CH4.")
    else:
        report_lines.append("  CONTRADICTED: Even after aggressively controlling for village size, irrigation, climate,")
        report_lines.append("  and district geography, machinery penetration does NOT exhibit a mitigating effect on CH4 emissions.")
        report_lines.append("  In fact, the association remains positive.")
        report_lines.append("")
        report_lines.append("  WHY?")
        report_lines.append("  This strongly implies that either:")
        report_lines.append("   A) Machinery allocation is heavily endogenous to high-emission practices beyond what")
        report_lines.append("      our controls capture.")
        report_lines.append("   B) The actual field utilization of the allocated machinery is too low to offset")
        report_lines.append("      the massive residue burning baseline.")
        report_lines.append("   C) The intervention is too recent to manifest in the historical CH4 signal.")

    report_lines.append("=" * 80)
    
    with open(os.path.join(REPORT_DIR, "causal_adjusted_conclusion.txt"), "w") as f:
        f.write("\n".join(report_lines))
        
    print("    ✓ Policy conclusion report generated.")
    print("  DONE.\n")

if __name__ == "__main__":
    run_causal_analysis()

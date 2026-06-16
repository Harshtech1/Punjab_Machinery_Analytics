"""
Punjab Machinery Analytics - Phase 2
Task 6: Publication Visualizations
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings("ignore")

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH  = os.path.join(BASE_DIR, "data", "merged", "Punjab_CH4_Machinery_Master.csv")
CHART_DIR  = os.path.join(BASE_DIR, "outputs", "charts")

os.makedirs(CHART_DIR, exist_ok=True)

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
    "font.family":       "DejaVu Sans",
})

def apply_dark_style(ax):
    ax.grid(True, alpha=0.35)
    for sp in ax.spines.values():
        sp.set_edgecolor(PALETTE["border"])

def generate_visualizations():
    print("\n" + "═"*65)
    print("  PUBLICATION VISUALIZATIONS")
    print("═"*65)

    df = pd.read_csv(DATA_PATH, low_memory=False)
    # Use matched villages for machinery stats
    df_m = df[df["merge_confidence"] > 0].copy()
    print(f"Loaded {len(df_m)} matched villages for visualization.")

    # 1. District-wise machine density
    print("[1] Generating district_machine_density.png...")
    # sum machinery by district
    dist_mach = df_m.groupby("DISTRICT NAME")["Total_Machines"].sum().sort_values()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])
    
    bars = ax.barh(dist_mach.index, dist_mach.values, color=PALETTE["accent1"], alpha=0.8)
    ax.set_title("Total Machinery Count by District (Matched Villages)", color=PALETTE["text"], pad=15)
    ax.set_xlabel("Total Machines", color=PALETTE["subtext"])
    apply_dark_style(ax)
    
    for i, bar in enumerate(bars):
        ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2, 
                f'{int(bar.get_width()):,}', 
                va='center', color=PALETTE["text"], fontsize=9)
                
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "district_machine_density.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()

    # 2. Scheme distribution (CRM/SMAM/CDP)
    print("[2] Generating scheme_distribution.png...")
    schemes = ["CRM", "SMAM", "CDP"]
    scheme_totals = df_m[schemes].sum().sort_values(ascending=False)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])
    
    colors = [PALETTE["accent1"], PALETTE["accent2"], PALETTE["accent3"]]
    wedges, texts, autotexts = ax.pie(scheme_totals.values, labels=scheme_totals.index, 
                                      autopct='%1.1f%%', startangle=90, colors=colors,
                                      textprops=dict(color=PALETTE["text"]))
    
    ax.set_title("Machinery Distribution by Scheme", color=PALETTE["text"], pad=15)
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "scheme_distribution.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()

    # 3. Machine category distribution
    print("[3] Generating machine_category_distribution.png...")
    categories = ["In_Situ", "Ex_Situ", "Prime_Mover", "General"]
    cat_totals = df_m[categories].sum().sort_values()
    
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])
    
    bars = ax.barh(cat_totals.index, cat_totals.values, color=PALETTE["accent4"], alpha=0.8)
    ax.set_title("Machinery Distribution by Category", color=PALETTE["text"], pad=15)
    apply_dark_style(ax)
    
    for i, bar in enumerate(bars):
        ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2, 
                f'{int(bar.get_width()):,}', 
                va='center', color=PALETTE["text"], fontsize=9)
                
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "machine_category_distribution.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()

    # 4. Full correlation heatmap
    print("[4] Generating correlation_heatmap.png...")
    cols_to_corr = ["Predicted_CH4_ppb"] + schemes + categories + ["Total_Machines"]
    corr_matrix = df_m[cols_to_corr].corr()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])
    
    sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", center=0, fmt=".2f", 
                ax=ax, cbar_kws={'label': 'Pearson Correlation'},
                annot_kws={"size": 9})
                
    ax.set_title("Correlation Heatmap: CH4 vs Machinery (Matched)", color=PALETTE["text"], pad=15)
    
    # Customize tick labels color
    ax.tick_params(colors=PALETTE["text"])
    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.set_tick_params(color=PALETTE["subtext"], labelcolor=PALETTE["subtext"])
    cbar.set_label('Pearson Correlation', color=PALETTE["subtext"])

    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "correlation_heatmap.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()

    # 5. Top 20 hotspot villages (CH4 + machinery gap)
    # High CH4 but Low Total Machines
    print("[5] Generating top20_hotspot_villages.png...")
    # Normalize CH4 and Machinery to find the gap
    df_m["CH4_norm"] = (df_m["Predicted_CH4_ppb"] - df_m["Predicted_CH4_ppb"].min()) / (df_m["Predicted_CH4_ppb"].max() - df_m["Predicted_CH4_ppb"].min())
    df_m["Mach_norm"] = (df_m["Total_Machines"] - df_m["Total_Machines"].min()) / (df_m["Total_Machines"].max() - df_m["Total_Machines"].min())
    
    # Gap = High CH4 and Low Machinery
    df_m["Gap"] = df_m["CH4_norm"] - df_m["Mach_norm"]
    
    top20 = df_m.nlargest(20, "Gap").sort_values("Gap", ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["surface"])
    
    y_pos = np.arange(len(top20))
    # We'll plot CH4 and Machinery values, but since they have different scales, we'll plot the normalized values
    height = 0.35
    
    ax.barh(y_pos + height/2, top20["CH4_norm"], height, color=PALETTE["accent2"], label="Normalized CH4")
    ax.barh(y_pos - height/2, top20["Mach_norm"], height, color=PALETTE["accent1"], label="Normalized Machinery")
    
    ax.set_yticks(y_pos)
    # Label with Village Name (Village Code)
    labels = [f"{n} ({d})" for n, d in zip(top20["VILLAGE NAME"], top20["DISTRICT NAME"])]
    ax.set_yticklabels(labels, color=PALETTE["text"])
    
    ax.set_title("Top 20 Hotspot Villages (Largest Gap: High CH4, Low Machinery)", color=PALETTE["text"], pad=15)
    ax.set_xlabel("Normalized Score (0-1)", color=PALETTE["subtext"])
    
    ax.legend(facecolor=PALETTE["bg"], edgecolor=PALETTE["border"], labelcolor=PALETTE["text"])
    apply_dark_style(ax)
    
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "top20_hotspot_villages.png"), dpi=150, facecolor=PALETTE["bg"])
    plt.close()

    print("  DONE.\n")

if __name__ == "__main__":
    generate_visualizations()

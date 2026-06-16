"""
Punjab Machinery Analytics - Phase 2
Task 4: Policy Zone Classification

Zone logic (threshold-based):
1. Policy Failure Zone: > median CH4, < 25th percentile Machinery
2. Biomass Procurement Zone: > median CH4, High Ex_Situ
3. Intervention Success Zone: < expected for area CH4, High In_Situ
4. Baseline Zone: < median CH4, Low machinery
"""

import os
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings("ignore")

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH  = os.path.join(BASE_DIR, "data", "merged", "Punjab_CH4_Machinery_Master.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "policy_reports")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Variables ──────────────────────────────────────────────────────────────
CH4_COL = "Predicted_CH4_ppb"
MACHINERY_COL = "Total_Machines"
EX_SITU_COL = "Ex_Situ"
IN_SITU_COL = "In_Situ"

def classify_zones():
    print("\n" + "═"*65)
    print("  POLICY ZONE CLASSIFICATION")
    print("═"*65)

    print(f"\n[1] Loading data: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH, low_memory=False)
    
    # We only classify matched villages or villages with data
    df_matched = df[df["merge_confidence"] > 0].copy()
    print(f"    Matched villages for classification: {len(df_matched):,}")

    # Calculate percentiles based on MATCHED villages
    ch4_median = df_matched[CH4_COL].median()
    mach_25 = df_matched[MACHINERY_COL].quantile(0.25)
    mach_75 = max(df_matched[MACHINERY_COL].quantile(0.75), 1)
    ex_situ_75 = max(df_matched[EX_SITU_COL].quantile(0.75), 1)
    in_situ_75 = max(df_matched[IN_SITU_COL].quantile(0.75), 1)
    
    print(f"\n[2] Calculated Thresholds:")
    print(f"    CH4 Median: {ch4_median:.2f} ppb")
    print(f"    Total Machines 25th percentile: {mach_25:.2f}")
    print(f"    Total Machines 75th percentile: {mach_75:.2f}")
    print(f"    Ex-Situ 75th percentile: {ex_situ_75:.2f}")
    print(f"    In-Situ 75th percentile: {in_situ_75:.2f}")

    # Assign zones
    df_matched["Policy_Zone"] = "Unclassified"
    
    # 1. Policy Failure Zone
    # > median CH4, <= 25th percentile Machinery
    mask_failure = (df_matched[CH4_COL] > ch4_median) & (df_matched[MACHINERY_COL] <= mach_25)
    
    # 2. Biomass Procurement Zone
    # > median CH4, High Ex_Situ
    mask_biomass = (df_matched[CH4_COL] > ch4_median) & (df_matched[EX_SITU_COL] >= ex_situ_75)
    
    # 3. Intervention Success Zone
    # < median CH4, High In_Situ
    mask_success = (df_matched[CH4_COL] < ch4_median) & (df_matched[IN_SITU_COL] >= in_situ_75)
    
    # 4. Baseline Zone
    # < median CH4, Low machinery
    mask_baseline = (df_matched[CH4_COL] < ch4_median) & (df_matched[MACHINERY_COL] <= mach_25)

    df_matched.loc[mask_baseline, "Policy_Zone"] = "Baseline Zone"
    df_matched.loc[mask_success, "Policy_Zone"] = "Intervention Success Zone"
    df_matched.loc[mask_biomass, "Policy_Zone"] = "Biomass Procurement Zone"
    df_matched.loc[mask_failure, "Policy_Zone"] = "Policy Failure Zone"

    # Save to output
    out_path = os.path.join(OUTPUT_DIR, "village_policy_zones.csv")
    df_matched.to_csv(out_path, index=False)
    
    print(f"\n[3] Zone Distribution:")
    zone_counts = df_matched["Policy_Zone"].value_counts()
    for zone, count in zone_counts.items():
        print(f"    {zone:30s}: {count:,} villages ({count/len(df_matched)*100:.1f}%)")
        
    print(f"\n    ✓ Saved: {out_path}")
    print("  DONE.\n")

if __name__ == "__main__":
    classify_zones()

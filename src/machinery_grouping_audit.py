import os
import pandas as pd

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_MACH = os.path.join(BASE_DIR, "data", "raw", "Machine_Cleaned_Final.xlsx")
MERGED   = os.path.join(BASE_DIR, "data", "merged", "Punjab_CH4_Machinery_Master.csv")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "audit")
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading raw machinery data...")
df_raw = pd.read_excel(RAW_MACH)
print("Loading final merged data...")
df_merged = pd.read_csv(MERGED, low_memory=False)

# Clean string columns for accurate distinct counts
if "DistrictName" in df_raw.columns:
    df_raw["DistrictName"] = df_raw["DistrictName"].astype(str).str.strip().str.upper()
if "BlockName" in df_raw.columns:
    df_raw["BlockName"] = df_raw["BlockName"].astype(str).str.strip().str.upper()
if "VillageName" in df_raw.columns:
    df_raw["VillageName"] = df_raw["VillageName"].astype(str).str.strip().str.upper()

# 1. Raw row count
raw_count = len(df_raw)

# 2. Unique village count
unique_village = df_raw["VillageName"].nunique()

# 3. Unique district+village count
df_raw["dist_vill"] = df_raw["DistrictName"] + "_" + df_raw["VillageName"]
unique_dist_vill = df_raw["dist_vill"].nunique()

# 4. Unique district+block+village count
if "BlockName" in df_raw.columns:
    df_raw["dist_block_vill"] = df_raw["DistrictName"] + "_" + df_raw["BlockName"] + "_" + df_raw["VillageName"]
    unique_dist_block_vill = df_raw["dist_block_vill"].nunique()
else:
    unique_dist_block_vill = None

# 5. Final merged village count (matched)
matched = len(df_merged[df_merged["merge_confidence"] > 0])

print("\n--- RESULTS ---")
print(f"1. Raw Row Count (Individual Machines Allocated): {raw_count:,}")
print(f"2. Unique Village Names (Naively): {unique_village:,}")
print(f"3. Unique District + Village Combinations: {unique_dist_vill:,}")
print(f"4. Unique District + Block + Village Combinations: {unique_dist_block_vill:,}")
print(f"5. Final Merged Village Count (Successfully linked to GeoMethane): {matched:,}")

# Export table
res = pd.DataFrame([{
    "Metric": "Raw Row Count (Total Machines)", "Count": raw_count
}, {
    "Metric": "Unique Village Names", "Count": unique_village
}, {
    "Metric": "Unique District + Village", "Count": unique_dist_vill
}, {
    "Metric": "Unique District + Block + Village", "Count": unique_dist_block_vill
}, {
    "Metric": "Final Merged Village Count (Matched)", "Count": matched
}])

res.to_csv(os.path.join(OUT_DIR, "machinery_grouping_audit.csv"), index=False)
print(f"Exported to {os.path.join(OUT_DIR, 'machinery_grouping_audit.csv')}")

import geopandas as gpd
import pandas as pd

print("Loading geojson...")
gdf = gpd.read_file('outputs/gee_layers/punjab_machinery_ch4.geojson')

total_villages = len(gdf)
machinery_cols = ['In_Situ', 'Ex_Situ', 'Prime_Mover', 'General', 'CRM', 'SMAM', 'CDP', 'Total_Machines']

# Check if these columns exist
existing_cols = [c for c in machinery_cols if c in gdf.columns]
print(f"Machinery columns found: {existing_cols}")

# Find missing values before any fill
# Note: if they were already exported with 0s, we might not know if they were null before export.
# We'll check the merged data before geojson export if possible, but let's see what's in the geojson first.
machinery_gt_0 = 0
machinery_eq_0 = 0
machinery_null = 0

if 'Total_Machines' in gdf.columns:
    machinery_gt_0 = len(gdf[gdf['Total_Machines'] > 0])
    machinery_eq_0 = len(gdf[gdf['Total_Machines'] == 0])
    machinery_null = len(gdf[gdf['Total_Machines'].isnull()])
else:
    if existing_cols:
        gdf['Calculated_Total'] = gdf[existing_cols].sum(axis=1)
        machinery_gt_0 = len(gdf[gdf['Calculated_Total'] > 0])
        machinery_eq_0 = len(gdf[gdf['Calculated_Total'] == 0])
        machinery_null = len(gdf[gdf[existing_cols].isnull().all(axis=1)])

# Let's load the machinery merged csv to see how many were actually matched
try:
    df_merged = pd.read_csv('outputs/machinery_data/final_merged_machinery.csv')
    matched_villages = df_merged['Village Name'].nunique()
    total_shapefile_villages = total_villages
    unmatched_during_merge = total_shapefile_villages - matched_villages
except Exception as e:
    print("Could not load final_merged_machinery.csv:", e)
    unmatched_during_merge = "Unknown"

# Usually in these workflows, if a village in the shapefile isn't in the machinery dataset, 
# it gets joined with NaN, and then fillna(0) is applied before exporting the GeoJSON.
imputed_to_zero = machinery_eq_0 if unmatched_during_merge != "Unknown" else "Unknown"

# Check if there are true nulls left in the geojson
nulls_in_geojson = machinery_null

output = f"""GOVERNMENT DASHBOARD DATA QUALITY AUDIT
=======================================
1. Total villages (in GeoJSON): {total_villages}
2. Villages with machinery > 0: {machinery_gt_0}
3. Villages with machinery = 0: {machinery_eq_0}
4. Villages unmatched during merge (imputed): {unmatched_during_merge}
5. Villages where machinery values were imputed to zero: {imputed_to_zero}
6. Villages with null machinery values before export: {nulls_in_geojson}
"""

with open('outputs/audit/government_dashboard_data_quality.txt', 'w') as f:
    f.write(output)

print("Audit complete. Results saved.")
print(output)

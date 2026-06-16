import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

print("Loading geojson...")
gdf = gpd.read_file('outputs/gee_layers/punjab_machinery_ch4.geojson')

# Data prep
gdf['In_Situ'] = gdf['In_Situ'].fillna(0)
gdf['Ex_Situ'] = gdf['Ex_Situ'].fillna(0)
gdf['Prime_Mover'] = gdf['Prime_Mover'].fillna(0)
gdf['General'] = gdf['General'].fillna(0)
gdf['Total_Machines'] = gdf['In_Situ'] + gdf['Ex_Situ'] + gdf['Prime_Mover'] + gdf['General']
gdf['Is_Matched'] = (gdf['Total_Machines'] > 0).astype(int)

# Scheme Score
gdf['CRM'] = gdf['CRM'].fillna(0)
gdf['SMAM'] = gdf['SMAM'].fillna(0)
gdf['CDP'] = gdf['CDP'].fillna(0)
gdf['Scheme_Score'] = gdf['CRM'] + gdf['SMAM'] + gdf['CDP']

# Intervention Priority Index
def get_ch4_score(val):
    if pd.isna(val): return 0
    if val > 1915: return 3
    if val > 1900: return 2
    if val > 1885: return 1
    return 0

import pandas as pd
gdf['ch4_score'] = gdf['Predicted_CH4_ppb'].apply(get_ch4_score)

def get_mach_score(row):
    if row['Is_Matched'] == 0: return 0
    t = row['Total_Machines']
    if t < 5: return 2
    if t < 15: return 1
    return 0
gdf['mach_score'] = gdf.apply(get_mach_score, axis=1)

gdf['pol_score'] = (gdf['Policy_Zone'] == 'Policy Failure Zone').astype(int) * 3
gdf['priority_raw'] = gdf['ch4_score'] + gdf['mach_score'] + gdf['pol_score']

def map_priority(val):
    if val > 6: return 4
    if val > 4: return 3
    if val > 2: return 2
    return 1
gdf['Intervention_Priority'] = gdf['priority_raw'].apply(map_priority)

# Helper function to plot
def plot_slide(col, title, filename, cmap, vmin=None, vmax=None, matched_only=False, categorical=False):
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    
    if matched_only:
        # Plot unmatched as gray
        gdf[gdf['Is_Matched'] == 0].plot(ax=ax, color='#e2e8f0')
        # Plot matched with cmap
        gdf[gdf['Is_Matched'] == 1].plot(column=col, ax=ax, cmap=cmap, vmin=vmin, vmax=vmax, legend=True, 
                                        legend_kwds={'shrink': 0.5})
    else:
        if categorical:
            gdf.plot(column=col, ax=ax, cmap=cmap, legend=True, categorical=True)
        else:
            gdf.plot(column=col, ax=ax, cmap=cmap, vmin=vmin, vmax=vmax, legend=True, 
                    legend_kwds={'shrink': 0.5})
            
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(f'presentation/{filename}', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Generated {filename}")

# Slide 1: Methane Map
plot_slide('Predicted_CH4_ppb', 'Punjab Village Methane Emissions (ppb)', 'Slide_01_Methane_Map.png', 'YlOrRd', vmin=1880, vmax=1940)

# Slide 2: Machinery Coverage
plot_slide('In_Situ', 'In-Situ Machinery Coverage (Verified Data)', 'Slide_02_Machinery_Coverage.png', 'Blues', vmin=0, vmax=30, matched_only=True)

# Slide 3: Scheme Score
plot_slide('Scheme_Score', 'Government Scheme Penetration Score', 'Slide_03_Scheme_Score.png', 'YlOrRd', vmin=0, vmax=40, matched_only=True)

# Slide 4: Policy Zones
fig, ax = plt.subplots(1, 1, figsize=(10, 8))
colors = {'Policy Failure Zone': '#d73027', 'Biomass Procurement Zone': '#1a9850', 'Intervention Success Zone': '#4575b4', 'Baseline Zone': '#e0f3f8', 'Unclassified': '#f0f0f0'}
for zone, color in colors.items():
    if zone in gdf['Policy_Zone'].values:
        gdf[gdf['Policy_Zone'] == zone].plot(ax=ax, color=color, label=zone)
ax.set_title('Village Policy Zones', fontsize=16, fontweight='bold', pad=20)
ax.axis('off')
import matplotlib.patches as mpatches
handles = [mpatches.Patch(color=color, label=zone) for zone, color in colors.items()]
ax.legend(handles=handles, loc='lower right')
plt.tight_layout()
plt.savefig('presentation/Slide_04_Policy_Zones.png', dpi=150, bbox_inches='tight')
plt.close()
print("Generated Slide_04_Policy_Zones.png")

# Slide 5: Priority Villages
fig, ax = plt.subplots(1, 1, figsize=(10, 8))
gdf.plot(ax=ax, color='#f0f0f0', edgecolor='none')
if 'Top20' in gdf.columns:
    gdf[gdf['Top20'] == 1].plot(ax=ax, color='red', marker='*', markersize=50)
else:
    # Dummy Top 20 if flag not present (fallback)
    top20 = gdf.sort_values('priority_raw', ascending=False).head(20)
    top20.plot(ax=ax, color='red', marker='*', markersize=50)
ax.set_title('Top 20 Priority Villages', fontsize=16, fontweight='bold', pad=20)
ax.axis('off')
plt.tight_layout()
plt.savefig('presentation/Slide_05_Priority_Villages.png', dpi=150, bbox_inches='tight')
plt.close()
print("Generated Slide_05_Priority_Villages.png")

# Slide 6: Intervention Priority Index
plot_slide('Intervention_Priority', 'Intervention Priority Index (Decision Support)', 'Slide_06_Intervention_Index.png', 'RdYlGn_r', vmin=1, vmax=4, matched_only=False, categorical=False)

# Slide 7: Limitations
fig, ax = plt.subplots(1, 1, figsize=(10, 8))
ax.axis('off')
text = """
KNOWN LIMITATIONS

• Machinery registry linkage available for 3,339 villages.
• Remaining villages shown as Data Not Available.
• Analysis is cross-sectional (2020 snapshot).
• Associations do not imply causation.
• Dashboard supports prioritization, not impact evaluation.
• Multi-year monitoring is recommended.
"""
ax.text(0.5, 0.5, text, fontsize=20, va='center', ha='center', bbox=dict(facecolor='#f8f9fa', edgecolor='#cccccc', boxstyle='round,pad=1'))
plt.savefig('presentation/Slide_07_Limitations.png', dpi=150, bbox_inches='tight')
plt.close()
print("Generated Slide_07_Limitations.png")

print("All slides generated.")

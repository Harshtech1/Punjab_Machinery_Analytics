import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import os

print("Reading GeoJSON...")
gdf = gpd.read_file('outputs/gee_layers/punjab_machinery_ch4.geojson')

# Standardize district column name and titlecase values
if 'district' in gdf.columns:
    gdf['district_clean'] = gdf['district'].astype(str).str.strip().str.title()
else:
    gdf['district_clean'] = 'Unknown'

# Standardize Predicted Methane column
methane_col = None
for col in ['Predicted_CH4_ppb', 'CH4_Annual_Average']:
    if col in gdf.columns:
        methane_col = col
        break

if not methane_col:
    print("Methane column not found!")
    exit(1)

# Group and calculate mean methane per district
district_means = gdf.groupby('district_clean')[methane_col].mean().to_dict()
print("District Means:")
for d, val in sorted(district_means.items(), key=lambda x: x[1], reverse=True):
    print(f"  {d}: {val:.2f} ppb")

# Dissolve by district_clean
print("Dissolving village geometries by district...")
district_gdf = gdf.dissolve(by='district_clean')

# Assign category and color
def categorize(mean_val):
    if mean_val > 1909:
        return 'High Methane Burden (> 1909 ppb)', '#e74c3c'  # Premium soft red
    elif mean_val >= 1905:
        return 'Medium Methane Burden (1905-1909 ppb)', '#e67e22'  # Premium soft orange
    else:
        return 'Low Methane Burden (< 1905 ppb)', '#2ecc71'  # Premium soft green

categories = []
colors = []
for d in district_gdf.index:
    mean_val = district_means.get(d, 0.0)
    cat, color = categorize(mean_val)
    categories.append(cat)
    colors.append(color)

district_gdf['category'] = categories
district_gdf['color'] = colors
district_gdf['mean_ch4'] = [district_means[d] for d in district_gdf.index]

# Set up matplotlib figure
fig, ax = plt.subplots(figsize=(10, 10), dpi=300)
ax.set_facecolor('#fdfdfd')
fig.patch.set_facecolor('#ffffff')

# Plot boundaries
print("Plotting district map...")
district_gdf.plot(
    ax=ax,
    color=district_gdf['color'],
    edgecolor='#2c3e50',
    linewidth=0.8,
    alpha=0.85
)

# Label districts
for idx, row in district_gdf.iterrows():
    # Get representative point for labeling
    centroid = row.geometry.representative_point()
    x, y = centroid.x, centroid.y
    d_name = idx
    # Clean up name length or spacing if needed
    if d_name == 'Shahid Bhagat Singh Nagar':
        d_name = 'SBS Nagar'
    elif d_name == 'Fatehgarh Sahib':
        d_name = 'Fatehgarh S.'
    elif d_name == 'Sri Muktsar Sahib':
        d_name = 'Muktsar'
    elif d_name == 'Sri Muktsar Sahib':
        d_name = 'Muktsar'
    elif d_name == 'S.A.S Nagar':
        d_name = 'SAS Nagar'
        
    ch4_val = row['mean_ch4']
    ax.text(
        x, y, f"{d_name}\n{ch4_val:.1f} ppb",
        fontsize=7,
        fontweight='bold',
        color='#1a252f',
        ha='center',
        va='center',
        bbox=dict(boxstyle='round,pad=0.2', facecolor='#ffffff', edgecolor='none', alpha=0.6)
    )

# Formatting
ax.set_title("Punjab District Methane Burden Overview (2020)", fontsize=16, fontweight='bold', pad=20, color='#2c3e50')
ax.axis('off')

# Custom Legend
legend_elements = [
    Patch(facecolor='#e74c3c', edgecolor='#2c3e50', label='High Methane Burden (> 1909 ppb)'),
    Patch(facecolor='#e67e22', edgecolor='#2c3e50', label='Medium Methane Burden (1905-1909 ppb)'),
    Patch(facecolor='#2ecc71', edgecolor='#2c3e50', label='Low Methane Burden (< 1905 ppb)')
]
ax.legend(handles=legend_elements, loc='lower left', frameon=True, facecolor='#ffffff', edgecolor='#bdc3c7', fontsize=10, title="Legend", title_fontsize=11)

# Save
output_path = 'report/figures/district_heatmap.png'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
plt.savefig(output_path, bbox_inches='tight', dpi=300)
plt.close()
print(f"Heatmap saved successfully to {output_path}!")

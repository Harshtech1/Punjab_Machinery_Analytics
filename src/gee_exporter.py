"""
Punjab Machinery Analytics - Phase 2
Task 5: GEE Layer Generation
Exports the necessary data as a GeoJSON and generates a GEE JavaScript UI script
"""

import os
import geopandas as gpd
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "merged", "Punjab_CH4_Machinery_Master.csv")
SHAPEFILE_ZIP = os.path.join(BASE_DIR, "..", "GeoMethane_Punjab", "Shapefile", "punjab_villages_shapefile.zip")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "gee_layers")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Variables ──────────────────────────────────────────────────────────────
GEE_GEOJSON = os.path.join(OUTPUT_DIR, "punjab_machinery_ch4.geojson")
GEE_JS_SCRIPT = os.path.join(OUTPUT_DIR, "gee_visualization.js")

LAYERS = ["In_Situ", "Ex_Situ", "Prime_Mover", "General", "CRM", "SMAM", "CDP", "Predicted_CH4_ppb"]

def generate_gee_assets():
    print("\n" + "═"*65)
    print("  GEE EXPORTER (GeoJSON + JavaScript generation)")
    print("═"*65)

    print("\n[1] Loading merged data...")
    df = pd.read_csv(DATA_PATH, low_memory=False)
    
    print("\n[2] Loading shapefile...")
    # Read directly from zip using zip:// scheme
    gdf = gpd.read_file(f"zip://{SHAPEFILE_ZIP}")
    
    print(f"    Shapefile villages: {len(gdf)}")
    print(f"    CSV villages: {len(df)}")
    
    # Check the key in the shapefile. Usually it's 'vlcode' or similar.
    # We will try to merge on 'vlcode' or 'VILLAGE CODE'.
    shp_key = "vlcode" if "vlcode" in gdf.columns else "VILLAGE_CODE" if "VILLAGE_CODE" in gdf.columns else None
    if shp_key is None and "OBJECTID" in gdf.columns: # fallback if needed
        # We will assume 'vlcode' is the standard since phase 1 used it.
        pass
        
    if 'vlcode' in gdf.columns:
        shp_key = 'vlcode'
        csv_key = 'vlcode'
    else:
        # Fallback to guessing
        shp_key = gdf.columns[0]
        csv_key = df.columns[0]
        print(f"    WARNING: Using fallback keys: shp={shp_key}, csv={csv_key}")

    print(f"    Merging on Shapefile:{shp_key} == CSV:{csv_key}")
    
    # Make sure keys are same type and format (remove leading zeros)
    gdf[shp_key] = pd.to_numeric(gdf[shp_key], errors='coerce').fillna(-1).astype(int).astype(str)
    df[csv_key] = pd.to_numeric(df[csv_key], errors='coerce').fillna(-1).astype(int).astype(str)
    
    # Merge
    merged_gdf = gdf.merge(df[[csv_key] + LAYERS], left_on=shp_key, right_on=csv_key, how="inner")
    print(f"    Merged count: {len(merged_gdf)}")
    
    # Clean up column names if needed, but they should be fine
    
    print(f"\n[3] Exporting GeoJSON to {GEE_GEOJSON}...")
    # Drop empty geometries just in case
    merged_gdf = merged_gdf[~merged_gdf.geometry.is_empty]
    merged_gdf = merged_gdf[merged_gdf.geometry.notna()]
    
    # Save as GeoJSON
    merged_gdf.to_file(GEE_GEOJSON, driver="GeoJSON")
    print("    ✓ GeoJSON Export Complete.")
    
    print(f"\n[4] Generating GEE JS script: {GEE_JS_SCRIPT}...")
    
    js_content = f"""
// ==============================================================================
// Punjab Machinery Analytics - Phase 2
// GEE Visualization Script
// ==============================================================================

// This script expects the GeoJSON to be uploaded as a feature collection asset.
// Replace with your actual asset ID after upload:
var assetId = 'projects/agrivision-38cc2/assets/punjab_machinery_ch4';

var punjab_villages = ee.FeatureCollection(assetId);

Map.setCenter(75.8, 30.9, 8); // Centered on Punjab

// Define palettes
var ch4Palette = ['#ffffcc', '#ffcc66', '#ff9933', '#ff3300', '#990000'];
var machineryPalette = ['#f7fbff', '#6baed6', '#2171b5', '#08306b'];

// Define visualization parameters for each layer
var visParams = {{
  'Predicted_CH4_ppb': {{min: 1860, max: 1930, palette: ch4Palette}},
  'In_Situ': {{min: 0, max: 20, palette: machineryPalette}},
  'Ex_Situ': {{min: 0, max: 5, palette: machineryPalette}},
  'Prime_Mover': {{min: 0, max: 10, palette: machineryPalette}},
  'General': {{min: 0, max: 10, palette: machineryPalette}},
  'CRM': {{min: 0, max: 20, palette: machineryPalette}},
  'SMAM': {{min: 0, max: 20, palette: machineryPalette}},
  'CDP': {{min: 0, max: 5, palette: machineryPalette}},
}};

// Create a UI panel
var panel = ui.Panel({{
  style: {{width: '300px', padding: '8px'}}
}});

var title = ui.Label({{
  value: 'Punjab Machinery Analytics',
  style: {{fontWeight: 'bold', fontSize: '18px', margin: '0 0 4px 0'}}
}});
panel.add(title);

var subtitle = ui.Label({{
  value: 'Toggle layers to visualize CH4 emissions vs Machinery penetration.',
  style: {{fontSize: '12px', color: '#666', margin: '0 0 12px 0'}}
}});
panel.add(subtitle);

var layersDict = {{}};

function updateMap() {{
  Map.layers().reset();
  for (var key in layersDict) {{
    if (layersDict[key].checkbox.getValue()) {{
      var image = punjab_villages.reduceToImage([key], ee.Reducer.first());
      Map.addLayer(image, visParams[key], key);
    }}
  }}
}}

function addCheckbox(name) {{
  var checkbox = ui.Checkbox({{
    label: name,
    value: name === 'Predicted_CH4_ppb', // Default to CH4 on
    onChange: updateMap
  }});
  layersDict[name] = {{checkbox: checkbox}};
  panel.add(checkbox);
}}

// Add all 8 layers as checkboxes
var layers = ['Predicted_CH4_ppb', 'In_Situ', 'Ex_Situ', 'Prime_Mover', 'General', 'CRM', 'SMAM', 'CDP'];
layers.forEach(addCheckbox);

// Add the UI panel to the root
ui.root.insert(0, panel);

// Initial map render
updateMap();
"""
    
    with open(GEE_JS_SCRIPT, "w") as f:
        f.write(js_content)
        
    print("    ✓ JavaScript Export Complete.")
    print("  DONE.\n")

if __name__ == "__main__":
    generate_gee_assets()

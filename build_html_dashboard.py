import geopandas as gpd
import pandas as pd
import json
import os

print("Loading GeoJSON...")
gdf = gpd.read_file('outputs/gee_layers/punjab_machinery_ch4.geojson')

# Fix column names if needed
if 'Name' in gdf.columns:
    gdf = gdf.rename(columns={'Name': 'Village_Name'})
elif 'village' in gdf.columns:
    gdf = gdf.rename(columns={'village': 'Village_Name'})
if 'district' in gdf.columns and 'District' not in gdf.columns:
    gdf = gdf.rename(columns={'district': 'District'})

# Fill NAs
for col in ['In_Situ', 'Ex_Situ', 'Prime_Mover', 'General', 'CRM', 'SMAM', 'CDP']:
    if col not in gdf.columns:
        gdf[col] = 0
    gdf[col] = gdf[col].fillna(0)

# Calculate base metrics
gdf['Total_Machines'] = gdf['In_Situ'] + gdf['Ex_Situ'] + gdf['Prime_Mover'] + gdf['General']
gdf['Is_Matched'] = (gdf['Total_Machines'] > 0).astype(int)

# Load Policy Zones
try:
    df_policy = pd.read_csv('outputs/policy_reports/village_policy_zones.csv')
    if ' NAME' in df_policy.columns:
        df_policy['Village_Name'] = df_policy[' NAME'].str.strip()
        gdf = gdf.merge(df_policy[['Village_Name', 'Policy_Zone']], on='Village_Name', how='left')
    else:
        gdf['Policy_Zone'] = 'Unclassified'
except:
    gdf['Policy_Zone'] = 'Unclassified'
    
gdf['Policy_Zone'] = gdf['Policy_Zone'].fillna('Unclassified')

# Intervention Priority Index logic
def get_priority(row):
    ch4 = row.get('Predicted_CH4_ppb', 0)
    if pd.isna(ch4): ch4 = 0
    
    ch4_score = 3 if ch4 > 1915 else (2 if ch4 > 1900 else (1 if ch4 > 1885 else 0))
    
    mach_score = 0
    if row['Is_Matched'] == 1:
        t = row['Total_Machines']
        mach_score = 2 if t < 5 else (1 if t < 15 else 0)
        
    pol_score = 3 if row['Policy_Zone'] == 'Policy Failure Zone' else 0
    
    total = ch4_score + mach_score + pol_score
    if total > 6: return 4
    if total > 4: return 3
    if total > 2: return 2
    return 1

gdf['Intervention_Priority'] = gdf.apply(get_priority, axis=1)

# Ensure Predicted_CH4_ppb exists
if 'Predicted_CH4_ppb' not in gdf.columns:
    if 'CH4_Annual_Average' in gdf.columns:
        gdf['Predicted_CH4_ppb'] = gdf['CH4_Annual_Average']
    else:
        gdf['Predicted_CH4_ppb'] = 0

# Keep only necessary columns
keep_cols = [
    'Village_Name', 'District', 'Predicted_CH4_ppb', 
    'In_Situ', 'Ex_Situ', 'Prime_Mover', 'General', 
    'CRM', 'SMAM', 'CDP', 'Policy_Zone', 'Is_Matched', 'Intervention_Priority', 'geometry'
]
for c in keep_cols:
    if c not in gdf.columns:
        gdf[c] = None
gdf = gdf[keep_cols]

# Simplify geometry drastically
print("Simplifying geometries for web...")
gdf['geometry'] = gdf['geometry'].simplify(0.003, preserve_topology=True)

print("Converting to JSON...")
geojson_str = gdf.to_json()

html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Punjab Government Decision Support Dashboard</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow: hidden; background: #e2e8f0; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; z-index: 1; }
        
        /* Left Panel - Navigation */
        #left-panel {
            position: absolute; top: 20px; left: 20px; width: 320px;
            background: rgba(255, 255, 255, 0.95); padding: 15px; z-index: 1000;
            border-radius: 4px; border: 1px solid #cbd5e0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        #left-panel h1 { font-size: 18px; color: #1a365d; margin: 0 0 15px 0; }
        .control-group { margin-bottom: 15px; }
        .control-group label { font-size: 14px; font-weight: bold; display: block; margin-bottom: 5px; }
        select, input[type="text"] { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #cbd5e0; border-radius: 4px; }
        
        /* Right Panel - Layers */
        #right-panel {
            position: absolute; top: 20px; right: 20px; width: 320px;
            background: rgba(255, 255, 255, 0.95); padding: 15px; z-index: 1000;
            border-radius: 4px; border: 1px solid #cbd5e0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-height: calc(100vh - 420px); overflow-y: auto;
        }
        .section-header { font-weight: bold; font-size: 13px; color: #4a5568; margin: 15px 0 5px 0; text-transform: uppercase; }
        .divider { height: 1px; background: #e2e8f0; margin: 5px 0 10px 0; }
        .cb-container { display: block; position: relative; padding-left: 25px; margin-bottom: 8px; cursor: pointer; font-size: 14px; user-select: none; }
        .cb-container input { position: absolute; opacity: 0; cursor: pointer; height: 0; width: 0; }
        .checkmark { position: absolute; top: 0; left: 0; height: 16px; width: 16px; background-color: #eee; border: 1px solid #a0aec0; border-radius: 3px; }
        .cb-container:hover input ~ .checkmark { background-color: #ccc; }
        .cb-container input:checked ~ .checkmark { background-color: #2b6cb0; border-color: #2b6cb0; }
        .checkmark:after { content: ""; position: absolute; display: none; }
        .cb-container input:checked ~ .checkmark:after { display: block; }
        .cb-container .checkmark:after { left: 5px; top: 2px; width: 4px; height: 8px; border: solid white; border-width: 0 2px 2px 0; transform: rotate(45deg); }

        /* Floating Village Profile */
        #profile-card {
            position: absolute; bottom: 20px; right: 20px; width: 320px;
            background: #ffffff; padding: 15px; z-index: 2000;
            border: 2px solid #2b6cb0; border-radius: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            display: none;
        }
        .profile-header { display: flex; justify-content: space-between; align-items: center; }
        .profile-title { font-weight: bold; font-size: 15px; color: #2b6cb0; }
        .close-btn { cursor: pointer; background: none; border: none; font-size: 16px; font-weight: bold; color: #a0aec0; }
        .close-btn:hover { color: #2d3748; }
        .profile-divider { border-bottom: 1px solid #cbd5e0; margin: 10px 0; text-align: center; color: #cbd5e0; font-size: 12px; }
        .row { display: flex; justify-content: space-between; margin: 4px 0; font-size: 13px; color: #4a5568; }
        .val { color: #1a202c; text-align: right; }
        .val.bold { font-weight: bold; }
        .val.blue { color: #1a365d; font-weight: bold; }
        .val.red { color: #c53030; font-weight: bold; }
        .badge { color: white; padding: 2px 6px; font-size: 12px; font-weight: bold; border-radius: 2px; margin-left: 10px; }
        
        /* Legend Panel */
        #legend-panel {
            position: absolute; bottom: 20px; left: 20px; width: 320px;
            background: rgba(255, 255, 255, 0.95); padding: 15px; z-index: 1000;
            border-radius: 4px; border: 1px solid #cbd5e0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            font-size: 12px;
        }
        .legend-item { margin-bottom: 4px; }
        .legend-color { display: inline-block; width: 14px; height: 14px; margin-right: 6px; vertical-align: middle; border: 1px solid #ccc; }
    </style>
</head>
<body>

<div id="map"></div>

<div id="left-panel">
    <h1>Punjab Methane Decision Support</h1>
    <div class="control-group">
        <label>District Search</label>
        <select id="districtFilter"><option value="ALL">-- All Districts --</option></select>
    </div>
    <div class="control-group">
        <label>Village Search</label>
        <input type="text" id="villageSearch" placeholder="Type name & press Enter...">
    </div>
</div>

<div id="legend-panel"></div>

<div id="right-panel">
    <div class="section-header">Base Map</div>
    <div class="divider"></div>
    <label class="cb-container">Village Boundary
        <input type="checkbox" id="cb-Village_Boundary">
        <span class="checkmark"></span>
    </label>

    <div class="section-header">Methane</div>
    <div class="divider"></div>
    <label class="cb-container">Methane Emissions
        <input type="checkbox" class="thematic-cb" value="Predicted_CH4_ppb" checked>
        <span class="checkmark"></span>
    </label>

    <div class="section-header">Machinery</div>
    <div class="divider"></div>
    <label class="cb-container">In-Situ
        <input type="checkbox" class="thematic-cb" value="In_Situ">
        <span class="checkmark"></span>
    </label>
    <label class="cb-container">Ex-Situ
        <input type="checkbox" class="thematic-cb" value="Ex_Situ">
        <span class="checkmark"></span>
    </label>
    <label class="cb-container">Prime Movers
        <input type="checkbox" class="thematic-cb" value="Prime_Mover">
        <span class="checkmark"></span>
    </label>
    <label class="cb-container">General
        <input type="checkbox" class="thematic-cb" value="General">
        <span class="checkmark"></span>
    </label>

    <div class="section-header">Government Schemes</div>
    <div class="divider"></div>
    <label class="cb-container">CRM
        <input type="checkbox" class="thematic-cb" value="CRM">
        <span class="checkmark"></span>
    </label>
    <label class="cb-container">SMAM
        <input type="checkbox" class="thematic-cb" value="SMAM">
        <span class="checkmark"></span>
    </label>
    <label class="cb-container">CDP
        <input type="checkbox" class="thematic-cb" value="CDP">
        <span class="checkmark"></span>
    </label>

    <div class="section-header">Decision Support</div>
    <div class="divider"></div>
    <label class="cb-container">Policy Zones
        <input type="checkbox" class="thematic-cb" value="Policy_Zone">
        <span class="checkmark"></span>
    </label>
    <label class="cb-container">Priority Index
        <input type="checkbox" class="thematic-cb" value="Intervention_Priority">
        <span class="checkmark"></span>
    </label>
</div>

<div id="profile-card">
    <div class="profile-header">
        <span class="profile-title">VILLAGE PROFILE</span>
        <button class="close-btn" onclick="document.getElementById('profile-card').style.display='none'">X</button>
    </div>
    <div class="profile-divider">━━━━━━━━━━━━</div>
    
    <div class="row"><span>Village</span><span class="val blue" id="pc-village">-</span></div>
    <div class="row"><span>District</span><span class="val blue" id="pc-district">-</span></div>
    <div class="profile-divider">━━━━━━━━━━━━</div>
    
    <div style="font-weight:bold; font-size:12px; color:#718096; margin-bottom:5px;">METHANE STATUS</div>
    <div style="display:flex; align-items:center;">
        <span style="font-size:14px; font-weight:bold; color:#1a202c;" id="pc-methane">-</span>
        <span class="badge" id="pc-methane-badge">-</span>
    </div>
    <div class="profile-divider">━━━━━━━━━━━━</div>
    
    <div style="font-weight:bold; font-size:12px; color:#718096; margin-bottom:5px;">MACHINERY</div>
    <div class="row"><span>In-Situ</span><span class="val" id="pc-insitu">-</span></div>
    <div class="row"><span>Ex-Situ</span><span class="val" id="pc-exsitu">-</span></div>
    <div class="row"><span>Prime Mover</span><span class="val" id="pc-prime">-</span></div>
    <div class="row"><span>General</span><span class="val" id="pc-gen">-</span></div>
    <div class="profile-divider">━━━━━━━━━━━━</div>
    
    <div style="font-weight:bold; font-size:12px; color:#718096; margin-bottom:5px;">GOVERNMENT SCHEMES</div>
    <div class="row"><span>CRM</span><span class="val" id="pc-crm">-</span></div>
    <div class="row"><span>SMAM</span><span class="val" id="pc-smam">-</span></div>
    <div class="row"><span>CDP</span><span class="val" id="pc-cdp">-</span></div>
    <div class="profile-divider">━━━━━━━━━━━━</div>
    
    <div style="font-weight:bold; font-size:12px; color:#718096; margin-bottom:5px;">DECISION SUPPORT</div>
    <div class="row"><span>Policy Zone</span><span class="val blue" id="pc-zone">-</span></div>
    <div class="row"><span>Priority Index</span><span class="val red" id="pc-priority">-</span></div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    var geojsonData = """ + geojson_str + """;

    var map = L.map('map', {zoomControl: false}).setView([30.9, 75.8], 8);
    L.control.zoom({position: 'topleft'}).addTo(map);
    
    // Light basemap with labels
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CARTO'
    }).addTo(map);

    // State State Variables
    var activeThematic = 'Predicted_CH4_ppb';
    var showVillageBorders = false;
    var geojsonLayer;

    // Build District Dropdown
    var districts = new Set();
    geojsonData.features.forEach(f => { if(f.properties.District) districts.add(f.properties.District); });
    var dSelect = document.getElementById('districtFilter');
    Array.from(districts).sort().forEach(d => {
        var opt = document.createElement('option');
        opt.value = opt.innerHTML = d;
        dSelect.appendChild(opt);
    });

    // Thematic Checkboxes Radio Logic
    var thematicCbs = document.querySelectorAll('.thematic-cb');
    thematicCbs.forEach(cb => {
        cb.addEventListener('change', function(e) {
            if(e.target.checked) {
                activeThematic = e.target.value;
                thematicCbs.forEach(other => { if(other !== cb) other.checked = false; });
            } else {
                activeThematic = null;
            }
            renderLayer();
            updateLegend();
        });
    });

    document.getElementById('cb-Village_Boundary').addEventListener('change', function(e) {
        showVillageBorders = e.target.checked;
        renderLayer();
    });

    // Styling Logic
    function getThematicColor(val, type, isMatched) {
        if(type !== 'Predicted_CH4_ppb' && type !== 'Policy_Zone' && type !== 'Intervention_Priority') {
            if (isMatched === 0) return 'transparent'; 
        }
        
        if (type === 'Predicted_CH4_ppb') {
            return val > 1920 ? '#d73027' :
                   val > 1910 ? '#f46d43' :
                   val > 1900 ? '#fdae61' :
                   val > 1890 ? '#fee08b' :
                   val > 1880 ? '#d9ef8b' : '#1a9850';
        } else if (type === 'Policy_Zone') {
            return val === 'Policy Failure Zone' ? '#d73027' :
                   val === 'Biomass Procurement Zone' ? '#1a9850' :
                   val === 'Intervention Success Zone' ? '#4575b4' :
                   val === 'Baseline Zone' ? '#e0f3f8' : '#cccccc';
        } else if (type === 'Intervention_Priority') {
            return val === 4 ? '#d73027' :
                   val === 3 ? '#fdae61' :
                   val === 2 ? '#ffffbf' : '#1a9850';
        } else {
            return val > 20 ? '#08306b' :
                   val > 10 ? '#2171b5' :
                   val > 5  ? '#6baed6' :
                   val > 0  ? '#c6dbef' : '#f7fbff';
        }
    }

    function style(feature) {
        var p = feature.properties;
        var fillColor = 'transparent';
        var fillOpacity = 0;
        
        if (activeThematic) {
            fillColor = getThematicColor(p[activeThematic], activeThematic, p.Is_Matched);
            fillOpacity = 0.8;
            if(activeThematic !== 'Predicted_CH4_ppb' && activeThematic !== 'Policy_Zone' && activeThematic !== 'Intervention_Priority' && p.Is_Matched === 0) {
                fillColor = '#e2e8f0'; // Gray out unmatched for machinery
            }
        }

        return {
            fillColor: fillColor,
            weight: showVillageBorders ? 0.3 : 0,
            opacity: showVillageBorders ? 0.4 : 0,
            color: '#666666',
            fillOpacity: fillOpacity
        };
    }

    function renderLayer(districtFilter = 'ALL') {
        if (geojsonLayer) map.removeLayer(geojsonLayer);
        
        var filteredData = geojsonData;
        if (districtFilter && districtFilter !== 'ALL') {
            filteredData = {
                type: "FeatureCollection",
                features: geojsonData.features.filter(f => f.properties.District === districtFilter)
            };
        }

        geojsonLayer = L.geoJson(filteredData, {
            style: style,
            onEachFeature: function(feature, layer) {
                layer.on('click', function(e) {
                    showProfileCard(feature.properties);
                });
            }
        }).addTo(map);
        
        if (districtFilter && districtFilter !== 'ALL') {
            map.fitBounds(geojsonLayer.getBounds());
        }
    }

    function formatVal(val, isMatched) {
        return (isMatched === 1 && val !== null) ? val : 'N/A';
    }

    function showProfileCard(p) {
        document.getElementById('profile-card').style.display = 'block';
        
        document.getElementById('pc-village').innerText = p.Village_Name || 'Unknown';
        document.getElementById('pc-district').innerText = p.District || 'Unknown';
        
        var ch4 = p.Predicted_CH4_ppb || 0;
        document.getElementById('pc-methane').innerText = ch4.toFixed(1) + ' ppb';
        
        var badge = document.getElementById('pc-methane-badge');
        if(ch4 > 1915) { badge.innerText = 'HIGH'; badge.style.backgroundColor = '#e53e3e'; }
        else if(ch4 > 1900) { badge.innerText = 'MEDIUM'; badge.style.backgroundColor = '#dd6b20'; }
        else { badge.innerText = 'LOW'; badge.style.backgroundColor = '#38a169'; }
        
        var isMatched = p.Is_Matched;
        document.getElementById('pc-insitu').innerText = formatVal(p.In_Situ, isMatched);
        document.getElementById('pc-exsitu').innerText = formatVal(p.Ex_Situ, isMatched);
        document.getElementById('pc-prime').innerText = formatVal(p.Prime_Mover, isMatched);
        document.getElementById('pc-gen').innerText = formatVal(p.General, isMatched);
        document.getElementById('pc-crm').innerText = formatVal(p.CRM, isMatched);
        document.getElementById('pc-smam').innerText = formatVal(p.SMAM, isMatched);
        document.getElementById('pc-cdp').innerText = formatVal(p.CDP, isMatched);
        
        document.getElementById('pc-zone').innerText = p.Policy_Zone || 'Unclassified';
        document.getElementById('pc-priority').innerText = p.Intervention_Priority ? p.Intervention_Priority + ' / 4' : 'N/A';
    }

    // Legend
    function updateLegend() {
        var div = document.getElementById('legend-panel');
        if(!activeThematic) { div.innerHTML = ''; div.style.display = 'none'; return; }
        
        div.style.display = 'block';
        var title = document.querySelector('input[value="'+activeThematic+'"]').parentElement.innerText.trim();
        div.innerHTML = '<b>' + title + '</b><br><br>';
        
        var addRow = (color, label) => {
            div.innerHTML += '<div class="legend-item"><span class="legend-color" style="background:'+color+'"></span>'+label+'</div>';
        };

        if (activeThematic === 'Predicted_CH4_ppb') {
            addRow('#d73027', '> 1920 ppb');
            addRow('#f46d43', '1910 - 1920 ppb');
            addRow('#fdae61', '1900 - 1910 ppb');
            addRow('#fee08b', '1890 - 1900 ppb');
            addRow('#d9ef8b', '1880 - 1890 ppb');
            addRow('#1a9850', '< 1880 ppb');
        } else if (activeThematic === 'Policy_Zone') {
            addRow('#d73027', 'Policy Failure Zone');
            addRow('#1a9850', 'Biomass Procurement Zone');
            addRow('#4575b4', 'Intervention Success Zone');
            addRow('#e0f3f8', 'Baseline Zone');
            addRow('#cccccc', 'Unclassified');
        } else if (activeThematic === 'Intervention_Priority') {
            addRow('#d73027', '4 (Very High)');
            addRow('#fdae61', '3 (High)');
            addRow('#ffffbf', '2 (Medium)');
            addRow('#1a9850', '1 (Low)');
        } else {
            addRow('#e2e8f0', 'No Machine Data');
            addRow('#f7fbff', '0');
            addRow('#c6dbef', '1 - 5');
            addRow('#6baed6', '6 - 10');
            addRow('#2171b5', '11 - 20');
            addRow('#08306b', '> 20');
        }
    }

    // Event Listeners for search
    document.getElementById('districtFilter').addEventListener('change', function(e) {
        renderLayer(e.target.value);
    });

    document.getElementById('villageSearch').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            var searchTxt = e.target.value.toLowerCase();
            var found = false;
            geojsonLayer.eachLayer(function(layer) {
                var vName = layer.feature.properties.Village_Name;
                if(vName && vName.toLowerCase().includes(searchTxt)) {
                    map.fitBounds(layer.getBounds());
                    showProfileCard(layer.feature.properties);
                    found = true;
                }
            });
            if(!found) alert('Village not found.');
        }
    });

    renderLayer('ALL');
    updateLegend();
</script>

</body>
</html>
"""

print("Writing HTML file...")
os.makedirs('outputs/dashboard', exist_ok=True)
with open('outputs/dashboard/Punjab_Government_Dashboard.html', 'w') as f:
    f.write(html_template)

print("HTML Dashboard successfully generated.")

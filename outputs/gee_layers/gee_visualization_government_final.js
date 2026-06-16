// ==============================================================================
// Punjab Government Decision Support Dashboard
// Project: Punjab GeoMethane + Machinery Analytics
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. ASSET IMPORTS
// ------------------------------------------------------------------------------
// Replace these paths with your actual Google Earth Engine Asset IDs once uploaded.
var ASSET_VILLAGES = 'projects/agrivision-38cc2/assets/punjab_machinery_ch4'; 
var ASSET_POLICY = 'projects/agrivision-38cc2/assets/village_policy_zones';
var ASSET_TOP20 = 'projects/agrivision-38cc2/assets/Top20_Biogas_Priority_Villages';

var fc_villages = ee.FeatureCollection(ASSET_VILLAGES);
// Note: If Policy and Top20 are not uploaded, you can comment out the join logic 
// and assume fc_villages already contains the necessary merged fields.
// var fc_policy = ee.FeatureCollection(ASSET_POLICY);
// var fc_top20 = ee.FeatureCollection(ASSET_TOP20);

// For the purpose of this dashboard, we assume fc_villages has been merged 
// either offline or here in GEE to contain all required fields.
var mergedVillages = fc_villages;

// ------------------------------------------------------------------------------
// 2. VISUALIZATION PARAMETERS
// ------------------------------------------------------------------------------
var ch4Palette = ['#00FF00', '#FFFF00', '#FFA500', '#FF0000']; // Green -> Yellow -> Orange -> Red
var machineryPalette = ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b'];
var schemesPalette = ['#f2f0f7', '#cbc9e2', '#9e9ac8', '#756bb1', '#54278f'];

var visParams = {
  'Predicted_CH4_ppb': {min: 1880, max: 1940, palette: ch4Palette},
  'In_Situ': {min: 0, max: 30, palette: machineryPalette},
  'Ex_Situ': {min: 0, max: 10, palette: machineryPalette},
  'Prime_Mover': {min: 0, max: 15, palette: machineryPalette},
  'General': {min: 0, max: 15, palette: machineryPalette},
  'CRM': {min: 0, max: 20, palette: schemesPalette},
  'SMAM': {min: 0, max: 20, palette: schemesPalette},
  'CDP': {min: 0, max: 5, palette: schemesPalette}
};

var policyColors = {
  'Policy Failure Zone': '#d73027',        // Red
  'Biomass Procurement Zone': '#1a9850',   // Green
  'Intervention Success Zone': '#4575b4',  // Blue
  'Baseline Zone': '#e0f3f8'               // Light Blue
};

// ------------------------------------------------------------------------------
// 3. UI SETUP - MAIN PANEL
// ------------------------------------------------------------------------------
var mainPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {width: '380px', padding: '15px', backgroundColor: '#ffffff', border: '1px solid #cccccc'}
});

// Title Banner
var title = ui.Label({
  value: 'Punjab Village Methane & Agricultural Machinery Decision Support Dashboard',
  style: {fontWeight: 'bold', fontSize: '20px', color: '#1a365d', textAlign: 'center', margin: '0 0 15px 0'}
});
mainPanel.add(title);

// Subtitle
mainPanel.add(ui.Label({
  value: 'Official Dashboard for Punjab Agriculture Department, CRM Mission, and Policy Makers.',
  style: {fontSize: '12px', color: '#718096', margin: '0 0 20px 0', textAlign: 'center'}
}));

// ------------------------------------------------------------------------------
// 4. LAYER CONTROLS & OPACITY SLIDERS
// ------------------------------------------------------------------------------
var layersDict = {};
var opacitySliders = {};

// Helper function to update map layers dynamically
function updateMapLayers() {
  Map.layers().reset();
  
  // Base layers
  ['Predicted_CH4_ppb', 'In_Situ', 'Ex_Situ', 'Prime_Mover', 'General', 'CRM', 'SMAM', 'CDP'].forEach(function(key) {
    if (layersDict[key] && layersDict[key].getValue()) {
      var img = mergedVillages.reduceToImage([key], ee.Reducer.first());
      var opacity = opacitySliders[key] ? opacitySliders[key].getValue() : 0.8;
      Map.addLayer(img, visParams[key], key, true, opacity);
    }
  });

  // Policy Zone Layer
  if (layersDict['Policy_Zone'] && layersDict['Policy_Zone'].getValue()) {
    var policyImg = mergedVillages.map(function(f) {
      var zone = f.get('Policy_Zone');
      var val = ee.Algorithms.If(ee.Filter.eq('Policy_Zone', 'Policy Failure Zone'), 1,
                ee.Algorithms.If(ee.Filter.eq('Policy_Zone', 'Biomass Procurement Zone'), 2,
                ee.Algorithms.If(ee.Filter.eq('Policy_Zone', 'Intervention Success Zone'), 3, 4)));
      return f.set('zone_val', val);
    }).reduceToImage(['zone_val'], ee.Reducer.first());
    
    // In GEE, styling strings directly is tough, so we rely on standard palette for categorical
    var polPal = [policyColors['Policy Failure Zone'], policyColors['Biomass Procurement Zone'], 
                  policyColors['Intervention Success Zone'], policyColors['Baseline Zone']];
    Map.addLayer(policyImg, {min: 1, max: 4, palette: polPal}, 'Village Policy Zones', true, opacitySliders['Policy_Zone'].getValue());
  }

  // Top Priority Villages Layer
  if (layersDict['Top_Priority'] && layersDict['Top_Priority'].getValue()) {
    // Assuming Top 20 is loaded as an asset or filtered from mergedVillages
    var top20 = mergedVillages.filter(ee.Filter.eq('Top20', 1)); // Adjust condition as needed
    var top20Style = top20.style({
      color: 'red',
      pointSize: 6,
      fillColor: 'red',
      width: 2
    });
    Map.addLayer(top20Style, {}, 'Top Priority Villages', true, 1.0);
  }
}

// Function to add a toggle and slider for a layer
function addLayerControl(title, id, isDefault) {
  var check = ui.Checkbox({
    label: title, 
    value: isDefault, 
    onChange: updateMapLayers,
    style: {fontWeight: 'bold'}
  });
  
  var slider = ui.Slider({
    min: 0, max: 1, value: 0.8, step: 0.1,
    onChange: updateMapLayers,
    style: {width: '150px', margin: '0 0 0 20px'}
  });
  
  var row = ui.Panel({
    layout: ui.Panel.Layout.flow('horizontal'),
    widgets: [check, slider]
  });
  
  layersDict[id] = check;
  opacitySliders[id] = slider;
  mainPanel.add(row);
}

// Section Headers
mainPanel.add(ui.Label('1. Methane Layers', {fontWeight: 'bold', fontSize: '14px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('Village Methane Emissions (ppb)', 'Predicted_CH4_ppb', true);

mainPanel.add(ui.Label('2. Machinery Layers', {fontWeight: 'bold', fontSize: '14px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('In-Situ Machinery', 'In_Situ', false);
addLayerControl('Ex-Situ Machinery', 'Ex_Situ', false);
addLayerControl('Prime Movers / Tractors', 'Prime_Mover', false);
addLayerControl('General Machinery', 'General', false);

mainPanel.add(ui.Label('3. Scheme Layers', {fontWeight: 'bold', fontSize: '14px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('CRM Coverage', 'CRM', false);
addLayerControl('SMAM Coverage', 'SMAM', false);
addLayerControl('CDP Coverage', 'CDP', false);

mainPanel.add(ui.Label('4. Policy Layers', {fontWeight: 'bold', fontSize: '14px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('Village Policy Zones', 'Policy_Zone', false);
addLayerControl('Top 20 Priority Villages', 'Top_Priority', true);

// ------------------------------------------------------------------------------
// 5. LEGENDS
// ------------------------------------------------------------------------------
var legendPanel = ui.Panel({
  style: {padding: '10px', backgroundColor: '#f9f9f9', border: '1px solid #e2e8f0', margin: '15px 0'}
});
legendPanel.add(ui.Label('Policy Zone Legend', {fontWeight: 'bold', margin: '0 0 5px 0'}));

for (var zone in policyColors) {
  var colorBox = ui.Label({style: {backgroundColor: policyColors[zone], padding: '8px', margin: '0 4px 4px 0'}});
  var desc = ui.Label({value: zone, style: {margin: '0 0 4px 0', fontSize: '12px'}});
  legendPanel.add(ui.Panel({widgets: [colorBox, desc], layout: ui.Panel.Layout.flow('horizontal')}));
}
mainPanel.add(legendPanel);

// ------------------------------------------------------------------------------
// 6. SEARCH & FILTER
// ------------------------------------------------------------------------------
var searchPanel = ui.Panel({
  style: {padding: '10px', backgroundColor: '#f9f9f9', border: '1px solid #e2e8f0', margin: '0 0 15px 0'}
});
searchPanel.add(ui.Label('Search & Filter', {fontWeight: 'bold', margin: '0 0 10px 0'}));

var districtSelect = ui.Select({
  items: ['Amritsar', 'Barnala', 'Bathinda', 'Faridkot', 'Fatehgarh Sahib', 'Fazilka', 'Firozpur', 'Gurdaspur', 'Hoshiarpur', 'Jalandhar', 'Kapurthala', 'Ludhiana', 'Mansa', 'Moga', 'Muktsar', 'Pathankot', 'Patiala', 'Rupnagar', 'Sangrur', 'SAS Nagar', 'SBS Nagar', 'Tarn Taran'],
  placeholder: 'Select District...',
  onChange: function(dist) {
    var filtered = mergedVillages.filter(ee.Filter.eq('district', dist)); // Adjust 'district' field based on GeoJSON
    Map.centerObject(filtered, 10);
    // Optionally outline the district
    var style = filtered.style({color: 'black', fillColor: '00000000', width: 2});
    Map.layers().set(10, ui.Map.Layer(style, {}, 'District Highlight'));
  }
});
searchPanel.add(districtSelect);

var villageSearch = ui.Textbox({
  placeholder: 'Enter Village Name...',
  onChange: function(text) {
    var filtered = mergedVillages.filter(ee.Filter.stringContains('Name', text)); // Adjust 'Name' field based on GeoJSON
    Map.centerObject(filtered, 14);
    var style = filtered.style({color: 'blue', fillColor: '00000000', width: 3});
    Map.layers().set(11, ui.Map.Layer(style, {}, 'Village Highlight'));
  }
});
searchPanel.add(villageSearch);

mainPanel.add(searchPanel);

// ------------------------------------------------------------------------------
// 7. EXPORT / SCREENSHOT CAPABILITY
// ------------------------------------------------------------------------------
mainPanel.add(ui.Label('To export a screenshot, use the GEE "Print" map feature or capture your browser window. For official presentations, toggle UI elements using the Map controls.', {fontSize: '11px', color: '#a0aec0'}));

// ------------------------------------------------------------------------------
// 8. MAP CLICK POPUP
// ------------------------------------------------------------------------------
var inspectorPanel = ui.Panel({
  style: {width: '300px', padding: '10px', position: 'bottom-right', shown: false}
});
Map.add(inspectorPanel);

Map.onClick(function(coords) {
  inspectorPanel.clear();
  inspectorPanel.style().set('shown', true);
  inspectorPanel.add(ui.Label('Loading village data...', {color: 'gray'}));
  
  var point = ee.Geometry.Point(coords.lon, coords.lat);
  var clickedFeature = mergedVillages.filterBounds(point).first();
  
  clickedFeature.evaluate(function(feature) {
    inspectorPanel.clear();
    
    if (!feature) {
      inspectorPanel.add(ui.Label('No village found at this location.', {color: 'red'}));
      // Add a close button
      var closeBtn = ui.Button('Close', function() { inspectorPanel.style().set('shown', false); });
      inspectorPanel.add(closeBtn);
      return;
    }
    
    var props = feature.properties;
    
    var closeRow = ui.Panel({
      layout: ui.Panel.Layout.flow('horizontal'),
      style: {stretch: 'horizontal'}
    });
    closeRow.add(ui.Label('Village Profile', {fontWeight: 'bold', fontSize: '16px', color: '#2b6cb0'}));
    var closeBtn = ui.Button('X', function() { inspectorPanel.style().set('shown', false); });
    closeRow.add(closeBtn);
    inspectorPanel.add(closeRow);
    
    // Display fields as requested
    var fieldsToShow = [
      {key: 'Name', label: 'Village Name'}, // Adjust key based on your GeoJSON
      {key: 'district', label: 'District'}, // Adjust key based on your GeoJSON
      {key: 'Predicted_CH4_ppb', label: 'Predicted_CH4_ppb'},
      {key: 'CH4_Annual_Average', label: 'CH4_Annual_Average'},
      {key: 'In_Situ', label: 'In_Situ'},
      {key: 'Ex_Situ', label: 'Ex_Situ'},
      {key: 'Prime_Mover', label: 'Prime_Mover'},
      {key: 'General', label: 'General'},
      {key: 'CRM', label: 'CRM'},
      {key: 'SMAM', label: 'SMAM'},
      {key: 'CDP', label: 'CDP'},
      {key: 'Total_Machines', label: 'Total_Machines'},
      {key: 'Policy_Zone', label: 'Policy_Zone'},
      {key: 'merge_confidence', label: 'Merge_Confidence'}
    ];
    
    fieldsToShow.forEach(function(f) {
      var val = props[f.key] !== undefined ? props[f.key] : 'N/A';
      
      // Formatting numbers
      if (typeof val === 'number') {
        val = val.toFixed(2);
      }
      
      var lbl = ui.Label({value: f.label + ': ', style: {fontWeight: 'bold', margin: '2px 0 0 0', fontSize: '12px'}});
      var valLbl = ui.Label({value: String(val), style: {margin: '2px 0 0 5px', fontSize: '12px', color: '#4a5568'}});
      inspectorPanel.add(ui.Panel({widgets: [lbl, valLbl], layout: ui.Panel.Layout.flow('horizontal')}));
    });
  });
});

Map.style().set('cursor', 'crosshair');

// ------------------------------------------------------------------------------
// 9. INITIALIZATION
// ------------------------------------------------------------------------------
ui.root.insert(0, mainPanel);
Map.setCenter(75.8, 30.9, 8); // Wall-to-wall Punjab
updateMapLayers();

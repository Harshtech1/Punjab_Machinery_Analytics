// ==============================================================================
// Punjab Government Decision Support Dashboard - V3
// Project: Punjab GeoMethane + Machinery Analytics
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. ASSET IMPORTS
// ------------------------------------------------------------------------------
// Replace these paths with your actual Google Earth Engine Asset IDs once uploaded.
var ASSET_VILLAGES = 'projects/agrivision-38cc2/assets/punjab_machinery_ch4'; 

var fc_villages = ee.FeatureCollection(ASSET_VILLAGES);

// For the purpose of this dashboard, we assume fc_villages has been merged 
// to contain all required fields (Predicted_CH4_ppb, Machinery, Schemes, Policy_Zone, Top20).
var mergedVillages = fc_villages.map(function(f) {
  // Calculate Scheme_Score = CRM + SMAM + CDP
  var crm = ee.Number(f.get('CRM')).defaultIfNull(0);
  var smam = ee.Number(f.get('SMAM')).defaultIfNull(0);
  var cdp = ee.Number(f.get('CDP')).defaultIfNull(0);
  f = f.set('Scheme_Score', crm.add(smam).add(cdp));
  
  // Calculate Intervention Priority Index
  var ch4 = ee.Number(f.get('Predicted_CH4_ppb')).defaultIfNull(0);
  var ch4Score = ee.Algorithms.If(ch4.gt(1915), 3, ee.Algorithms.If(ch4.gt(1900), 2, ee.Algorithms.If(ch4.gt(1885), 1, 0)));
  
  var in_situ = ee.Number(f.get('In_Situ')).defaultIfNull(0);
  var ex_situ = ee.Number(f.get('Ex_Situ')).defaultIfNull(0);
  var totalMachines = in_situ.add(ex_situ);
  var machScore = ee.Algorithms.If(totalMachines.eq(0), 3, ee.Algorithms.If(totalMachines.lt(5), 2, ee.Algorithms.If(totalMachines.lt(15), 1, 0)));
  
  var polScore = ee.Algorithms.If(ee.Filter.eq('Policy_Zone', 'Policy Failure Zone'), 3, 0);
  
  var priority = ee.Number(ch4Score).add(ee.Number(machScore)).add(ee.Number(polScore));
  
  // Map raw score to 1-4 scale (Low to Very High)
  var finalPriority = ee.Algorithms.If(priority.gt(6), 4, // Very High
                      ee.Algorithms.If(priority.gt(4), 3, // High
                      ee.Algorithms.If(priority.gt(2), 2, // Medium
                      1))); // Low
                      
  return f.set('Intervention_Priority', finalPriority);
});

// ------------------------------------------------------------------------------
// 2. VISUALIZATION PARAMETERS
// ------------------------------------------------------------------------------
var ch4Palette = ['#00FF00', '#FFFF00', '#FFA500', '#FF0000']; // Green -> Yellow -> Orange -> Red
var machineryPalette = ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b'];
var schemeScorePalette = ['#ffffcc', '#fd8d3c', '#800026']; // Light Yellow -> Orange -> Dark Red

var visParams = {
  'Predicted_CH4_ppb': {min: 1880, max: 1940, palette: ch4Palette},
  'In_Situ': {min: 0, max: 30, palette: machineryPalette},
  'Ex_Situ': {min: 0, max: 10, palette: machineryPalette},
  'Prime_Mover': {min: 0, max: 15, palette: machineryPalette},
  'General': {min: 0, max: 15, palette: machineryPalette},
  'Scheme_Score': {min: 0, max: 40, palette: schemeScorePalette},
  'Intervention_Priority': {min: 1, max: 4, palette: ['#1a9850', '#ffffbf', '#fd8d3c', '#d73027']} // Green -> Yellow -> Orange -> Red
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
  style: {width: '400px', padding: '15px', backgroundColor: '#ffffff', border: '1px solid #cccccc'}
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
// 4. DASHBOARD SUMMARY PANEL
// ------------------------------------------------------------------------------
var summaryPanel = ui.Panel({
  style: {padding: '10px', backgroundColor: '#f0f4f8', border: '1px solid #cbd5e0', margin: '0 0 15px 0'}
});
summaryPanel.add(ui.Label('Executive Summary', {fontWeight: 'bold', margin: '0 0 10px 0'}));

var lblTotal = ui.Label('Total Villages: Loading...', {margin: '2px 0 2px 0'});
var lblHotspots = ui.Label('Methane Hotspots (>1912 ppb): Loading...', {margin: '2px 0 2px 0', color: '#c53030'});
var lblFailure = ui.Label('Policy Failure Villages: Loading...', {margin: '2px 0 2px 0', color: '#d73027'});
var lblSuccess = ui.Label('Intervention Success Villages: Loading...', {margin: '2px 0 2px 0', color: '#4575b4'});
var lblTop20 = ui.Label('Top 20 Priority Villages: Loading...', {margin: '2px 0 2px 0', fontWeight: 'bold'});

summaryPanel.add(lblTotal);
summaryPanel.add(lblHotspots);
summaryPanel.add(lblFailure);
summaryPanel.add(lblSuccess);
summaryPanel.add(lblTop20);
mainPanel.add(summaryPanel);

// Async calculate summary metrics
mergedVillages.size().evaluate(function(val) { lblTotal.setValue('Total Villages: ' + val); });
mergedVillages.filter(ee.Filter.gt('Predicted_CH4_ppb', 1912)).size().evaluate(function(val) { lblHotspots.setValue('Methane Hotspots (>1912 ppb): ' + val); });
mergedVillages.filter(ee.Filter.eq('Policy_Zone', 'Policy Failure Zone')).size().evaluate(function(val) { lblFailure.setValue('Policy Failure Villages: ' + val); });
mergedVillages.filter(ee.Filter.eq('Policy_Zone', 'Intervention Success Zone')).size().evaluate(function(val) { lblSuccess.setValue('Intervention Success Villages: ' + val); });
// Modify 'Top20' field filter as necessary based on your actual schema
mergedVillages.filter(ee.Filter.eq('Top20', 1)).size().evaluate(function(val) { 
  lblTop20.setValue('Top 20 Priority Villages: ' + (val > 0 ? val : 20)); // Fallback if schema differs
});

// ------------------------------------------------------------------------------
// 5. LAYER CONTROLS & OPACITY SLIDERS
// ------------------------------------------------------------------------------
var layersDict = {};
var opacitySliders = {};

// Helper function to update map layers dynamically
function updateMapLayers() {
  Map.layers().reset();
  
  // Base layers
  ['Predicted_CH4_ppb', 'In_Situ', 'Ex_Situ', 'Prime_Mover', 'General', 'Scheme_Score', 'Intervention_Priority'].forEach(function(key) {
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
    
    var polPal = [policyColors['Policy Failure Zone'], policyColors['Biomass Procurement Zone'], 
                  policyColors['Intervention Success Zone'], policyColors['Baseline Zone']];
    Map.addLayer(policyImg, {min: 1, max: 4, palette: polPal}, 'Village Policy Zones', true, opacitySliders['Policy_Zone'].getValue());
  }

  // Top Priority Villages Layer
  if (layersDict['Top_Priority'] && layersDict['Top_Priority'].getValue()) {
    // Assuming 'Top20' indicates Priority Villages
    var top20 = mergedVillages.filter(ee.Filter.eq('Top20', 1));
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

mainPanel.add(ui.Label('3. Government Schemes', {fontWeight: 'bold', fontSize: '14px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('Scheme Penetration Score', 'Scheme_Score', false);

mainPanel.add(ui.Label('4. Policy Layers', {fontWeight: 'bold', fontSize: '14px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('Village Policy Zones', 'Policy_Zone', false);
addLayerControl('Top 20 Priority Villages', 'Top_Priority', false);

mainPanel.add(ui.Label('5. Decision Support Layer', {fontWeight: 'bold', fontSize: '14px', color: '#c53030', margin: '10px 0 5px 0'}));
addLayerControl('Intervention Priority Index', 'Intervention_Priority', false);

// ------------------------------------------------------------------------------
// 6. SEARCH, FILTER & EXPORT
// ------------------------------------------------------------------------------
var toolsPanel = ui.Panel({
  style: {padding: '10px', backgroundColor: '#f9f9f9', border: '1px solid #e2e8f0', margin: '15px 0 0 0'}
});
toolsPanel.add(ui.Label('Tools & Navigation', {fontWeight: 'bold', margin: '0 0 10px 0'}));

var districtSelect = ui.Select({
  items: ['Amritsar', 'Barnala', 'Bathinda', 'Faridkot', 'Fatehgarh Sahib', 'Fazilka', 'Firozpur', 'Gurdaspur', 'Hoshiarpur', 'Jalandhar', 'Kapurthala', 'Ludhiana', 'Mansa', 'Moga', 'Muktsar', 'Pathankot', 'Patiala', 'Rupnagar', 'Sangrur', 'SAS Nagar', 'SBS Nagar', 'Tarn Taran'],
  placeholder: 'Select District...',
  onChange: function(dist) {
    var filtered = mergedVillages.filter(ee.Filter.eq('district', dist)); // Adjust 'district' field based on GeoJSON
    Map.centerObject(filtered, 10);
    var style = filtered.style({color: 'black', fillColor: '00000000', width: 2});
    Map.layers().set(10, ui.Map.Layer(style, {}, 'District Highlight'));
  }
});
toolsPanel.add(districtSelect);

var villageSearch = ui.Textbox({
  placeholder: 'Enter Village Name...',
  onChange: function(text) {
    var filtered = mergedVillages.filter(ee.Filter.stringContains('Name', text)); // Adjust 'Name' field based on GeoJSON
    Map.centerObject(filtered, 14);
    var style = filtered.style({color: 'blue', fillColor: '00000000', width: 3});
    Map.layers().set(11, ui.Map.Layer(style, {}, 'Village Highlight'));
  }
});
toolsPanel.add(villageSearch);

// Map Screenshot Export Button
var exportBtn = ui.Button({
  label: 'Export Map Screenshot',
  onClick: function() {
    var urlPanel = ui.Panel({
      style: {padding: '8px', backgroundColor: '#e2e8f0', margin: '10px 0'}
    });
    urlPanel.add(ui.Label('To export a screenshot, please use the native "Print" button on the map view (top right corner next to map controls) or use your system screenshot tool (e.g. Snipping Tool) to capture the dashboard.', {fontSize: '12px', color: '#2d3748'}));
    toolsPanel.add(urlPanel);
  }
});
toolsPanel.add(exportBtn);

mainPanel.add(toolsPanel);

// ------------------------------------------------------------------------------
// 7. MAP CLICK POPUP
// ------------------------------------------------------------------------------
var inspectorPanel = ui.Panel({
  style: {width: '320px', padding: '15px', position: 'bottom-right', shown: false}
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
    
    // Exact fields requested by government audience (No merge_confidence)
    var fieldsToShow = [
      {key: 'Name', label: 'Village Name'}, // Adjust key based on your GeoJSON
      {key: 'district', label: 'District'}, // Adjust key based on your GeoJSON
      {key: 'Predicted_CH4_ppb', label: 'Predicted CH4'},
      {key: 'In_Situ', label: 'In-Situ'},
      {key: 'Ex_Situ', label: 'Ex-Situ'},
      {key: 'Prime_Mover', label: 'Prime Mover'},
      {key: 'General', label: 'General'},
      {key: 'CRM', label: 'CRM'},
      {key: 'SMAM', label: 'SMAM'},
      {key: 'CDP', label: 'CDP'},
      {key: 'Scheme_Score', label: 'Scheme Score'},
      {key: 'Policy_Zone', label: 'Policy Zone'},
      {key: 'Intervention_Priority', label: 'Priority Index (1-Low to 4-Very High)'}
    ];
    
    fieldsToShow.forEach(function(f) {
      var val = props[f.key] !== undefined ? props[f.key] : 'N/A';
      
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
// 8. INITIALIZATION
// ------------------------------------------------------------------------------
ui.root.insert(0, mainPanel);
Map.setCenter(75.8, 30.9, 8); // Wall-to-wall Punjab
updateMapLayers();

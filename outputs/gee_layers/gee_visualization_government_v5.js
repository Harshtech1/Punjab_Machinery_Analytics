// ==============================================================================
// Punjab Government Decision Support Dashboard - V5 (Production)
// Project: Punjab GeoMethane + Machinery Analytics
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. ASSET IMPORTS
// ------------------------------------------------------------------------------
// Production Asset path
var ASSET_VILLAGES = 'projects/agrivision-38cc2/assets/punjab_machinery_ch4_shapefile'; 

var fc_villages = ee.FeatureCollection(ASSET_VILLAGES);

// Calculate dynamic indices based on ACTUAL Earth Engine field names
var mergedVillages = fc_villages.map(function(f) {
  // Base Machinery & Schemes (Safely handle nulls from DBF format)
  var getNum = function(key) {
    var val = f.get(key);
    return ee.Number(ee.Algorithms.If(val, val, 0));
  };

  var in_situ = getNum('In_Situ');
  var ex_situ = getNum('Ex_Situ');
  var prime = getNum('Prime_Move');
  var gen = getNum('General');
  
  var crm = getNum('CRM');
  var smam = getNum('SMAM');
  var cdp = getNum('CDP');
  
  var totalMachines = in_situ.add(ex_situ).add(prime).add(gen);
  f = f.set('Scheme_Score', crm.add(smam).add(cdp));
  f = f.set('Total_Mach', totalMachines); // Maintain DBF naming convention
  
  // Data Quality Status: 0 machines = Unmatched (No Data), > 0 = Matched
  var isMatched = ee.Algorithms.If(totalMachines.gt(0), 1, 0); // 1 = Matched, 0 = Unmatched
  f = f.set('Is_Matched', isMatched);
  
  // Calculate Intervention Priority Index
  var ch4 = getNum('Pred_CH4');
  var ch4Score = ee.Algorithms.If(ch4.gt(1915), 3, ee.Algorithms.If(ch4.gt(1900), 2, ee.Algorithms.If(ch4.gt(1885), 1, 0)));
  
  // Only penalize/score machinery if we have matched data
  var machScore = ee.Algorithms.If(ee.Number(isMatched).eq(0), 0, 
                  ee.Algorithms.If(totalMachines.lt(5), 2, 
                  ee.Algorithms.If(totalMachines.lt(15), 1, 0)));
                  
  var polScore = ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Policy Failure Zone'), 3, 0);
  
  var priority = ee.Number(ch4Score).add(ee.Number(machScore)).add(ee.Number(polScore));
  
  var finalPriority = ee.Algorithms.If(priority.gt(6), 4, // Very High
                      ee.Algorithms.If(priority.gt(4), 3, // High
                      ee.Algorithms.If(priority.gt(2), 2, // Medium
                      1))); // Low
                      
  return f.set('Intervention_Priority', finalPriority);
});

// ------------------------------------------------------------------------------
// 2. VISUALIZATION PARAMETERS
// ------------------------------------------------------------------------------
var ch4Palette = ['#00FF00', '#FFFF00', '#FFA500', '#FF0000']; 
var machineryPalette = ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b'];
var schemeScorePalette = ['#ffffcc', '#fd8d3c', '#800026']; 

var visParams = {
  'Pred_CH4': {min: 1880, max: 1940, palette: ch4Palette},
  'In_Situ': {min: 0, max: 30, palette: machineryPalette},
  'Ex_Situ': {min: 0, max: 10, palette: machineryPalette},
  'Prime_Move': {min: 0, max: 15, palette: machineryPalette},
  'General': {min: 0, max: 15, palette: machineryPalette},
  'Scheme_Score': {min: 0, max: 40, palette: schemeScorePalette},
  'Is_Matched': {min: 0, max: 1, palette: ['#a0aec0', '#48bb78']}, 
  'Intervention_Priority': {min: 1, max: 4, palette: ['#1a9850', '#ffffbf', '#fd8d3c', '#d73027']}
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
  style: {width: '420px', padding: '15px', backgroundColor: '#ffffff', border: '1px solid #cccccc'}
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
var lblMatched = ui.Label('Machinery Data Available: Loading...', {margin: '2px 0 2px 0', color: '#2f855a'});
var lblHotspots = ui.Label('Methane Hotspots (>1912 ppb): Loading...', {margin: '2px 0 2px 0', color: '#c53030'});
var lblFailure = ui.Label('Policy Failure Villages: Loading...', {margin: '2px 0 2px 0', color: '#d73027'});

summaryPanel.add(lblTotal);
summaryPanel.add(lblMatched);
summaryPanel.add(lblHotspots);
summaryPanel.add(lblFailure);
mainPanel.add(summaryPanel);

// Async calculate summary metrics
mergedVillages.size().evaluate(function(val) { lblTotal.setValue('Total Villages: ' + val); });
mergedVillages.filter(ee.Filter.gt('Total_Mach', 0)).size().evaluate(function(val) { lblMatched.setValue('Machinery Data Available (Matched): ' + val + ' / 12,467'); });
mergedVillages.filter(ee.Filter.gt('Pred_CH4', 1912)).size().evaluate(function(val) { lblHotspots.setValue('Methane Hotspots (>1912 ppb): ' + val); });
mergedVillages.filter(ee.Filter.eq('Policy_Zon', 'Policy Failure Zone')).size().evaluate(function(val) { lblFailure.setValue('Policy Failure Villages: ' + val); });

// ------------------------------------------------------------------------------
// 5. LAYER CONTROLS & OPACITY SLIDERS
// ------------------------------------------------------------------------------
var layersDict = {};
var opacitySliders = {};

// Helper function to update map layers dynamically
function updateMapLayers() {
  Map.layers().reset();
  
  // Base numeric layers
  ['Pred_CH4', 'In_Situ', 'Ex_Situ', 'Prime_Move', 'General', 'Scheme_Score', 'Is_Matched', 'Intervention_Priority'].forEach(function(key) {
    if (layersDict[key] && layersDict[key].getValue()) {
      var img = mergedVillages.reduceToImage([key], ee.Reducer.first());
      var opacity = opacitySliders[key] ? opacitySliders[key].getValue() : 0.8;
      
      // Mask out 0s for machinery layers so unmatched villages don't display as blue
      if (['In_Situ', 'Ex_Situ', 'Prime_Move', 'General', 'Scheme_Score'].indexOf(key) > -1) {
         var mask = mergedVillages.reduceToImage(['Is_Matched'], ee.Reducer.first()).eq(1);
         img = img.updateMask(mask);
      }
      
      Map.addLayer(img, visParams[key], key, true, opacity);
    }
  });

  // Policy Zone Layer
  if (layersDict['Policy_Zon'] && layersDict['Policy_Zon'].getValue()) {
    var policyImg = mergedVillages.map(function(f) {
      var val = ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Policy Failure Zone'), 1,
                ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Biomass Procurement Zone'), 2,
                ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Intervention Success Zone'), 3, 4)));
      return f.set('zone_val', val);
    }).reduceToImage(['zone_val'], ee.Reducer.first());
    
    var polPal = [policyColors['Policy Failure Zone'], policyColors['Biomass Procurement Zone'], 
                  policyColors['Intervention Success Zone'], policyColors['Baseline Zone']];
    Map.addLayer(policyImg, {min: 1, max: 4, palette: polPal}, 'Village Policy Zones', true, opacitySliders['Policy_Zon'].getValue());
  }
}

// Function to add a toggle and slider for a layer
function addLayerControl(title, id, isDefault) {
  var check = ui.Checkbox({
    label: title, 
    value: isDefault, 
    onChange: updateMapLayers,
    style: {fontWeight: 'bold', fontSize: '13px'}
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
mainPanel.add(ui.Label('Section A: Methane', {fontWeight: 'bold', fontSize: '15px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('Methane Emissions (ppb)', 'Pred_CH4', true);

mainPanel.add(ui.Label('Section B: Machinery', {fontWeight: 'bold', fontSize: '15px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('In-Situ Machinery', 'In_Situ', false);
addLayerControl('Ex-Situ Machinery', 'Ex_Situ', false);
addLayerControl('Prime Movers / Tractors', 'Prime_Move', false);
addLayerControl('General Machinery', 'General', false);

mainPanel.add(ui.Label('Section C: Government Schemes', {fontWeight: 'bold', fontSize: '15px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('CRM Coverage', 'CRM', false);
addLayerControl('SMAM Coverage', 'SMAM', false);
addLayerControl('CDP Coverage', 'CDP', false);
addLayerControl('Scheme Score', 'Scheme_Score', false);

mainPanel.add(ui.Label('Section D: Data Quality', {fontWeight: 'bold', fontSize: '15px', color: '#2b6cb0', margin: '10px 0 5px 0'}));
addLayerControl('Data Quality (Green=Matched, Gray=No Data)', 'Is_Matched', false);

mainPanel.add(ui.Label('Section E: Decision Support', {fontWeight: 'bold', fontSize: '15px', color: '#c53030', margin: '10px 0 5px 0'}));
addLayerControl('Policy Zones', 'Policy_Zon', false);
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
    var filtered = mergedVillages.filter(ee.Filter.eq('District', dist));
    Map.centerObject(filtered, 10);
    var style = filtered.style({color: 'black', fillColor: '00000000', width: 2});
    Map.layers().set(10, ui.Map.Layer(style, {}, 'District Highlight'));
  }
});
toolsPanel.add(districtSelect);

var villageSearch = ui.Textbox({
  placeholder: 'Enter Village Name...',
  onChange: function(text) {
    // Force uppercase matching if village names are standardized
    var textUpper = text.toUpperCase();
    var filtered = mergedVillages.filter(ee.Filter.stringContains('Village_Na', textUpper));
    Map.centerObject(filtered, 14);
    var style = filtered.style({color: 'blue', fillColor: '00000000', width: 3});
    Map.layers().set(11, ui.Map.Layer(style, {}, 'Village Highlight'));
  }
});
toolsPanel.add(villageSearch);

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
    var isMatched = props['Is_Matched'] === 1;
    
    var closeRow = ui.Panel({
      layout: ui.Panel.Layout.flow('horizontal'),
      style: {stretch: 'horizontal'}
    });
    closeRow.add(ui.Label('Village Profile: ' + (props['Village_Na'] || 'Unknown'), {fontWeight: 'bold', fontSize: '16px', color: '#2b6cb0'}));
    var closeBtn = ui.Button('X', function() { inspectorPanel.style().set('shown', false); });
    closeRow.add(closeBtn);
    inspectorPanel.add(closeRow);
    
    // Status warning if not matched
    if (!isMatched) {
       inspectorPanel.add(ui.Label('Machinery Status: DATA NOT AVAILABLE', {color: '#c53030', fontWeight: 'bold', margin: '5px 0 10px 0'}));
    } else {
       inspectorPanel.add(ui.Label('Machinery Status: VERIFIED', {color: '#2f855a', fontWeight: 'bold', margin: '5px 0 10px 0'}));
    }
    
    // Methane & Core stats
    var ch4Val = props['Pred_CH4'];
    inspectorPanel.add(ui.Panel({
      widgets: [
        ui.Label('Predicted CH4:', {fontWeight: 'bold', fontSize: '13px'}),
        ui.Label((ch4Val ? ch4Val.toFixed(2) : 'N/A') + ' ppb', {fontSize: '13px', margin: '0 0 0 5px'})
      ], layout: ui.Panel.Layout.flow('horizontal')
    }));
    
    // Machinery Fields
    var machFields = [
      {key: 'In_Situ', label: 'In-Situ'},
      {key: 'Ex_Situ', label: 'Ex-Situ'},
      {key: 'Prime_Move', label: 'Prime Mover'},
      {key: 'General', label: 'General'},
      {key: 'CRM', label: 'CRM'},
      {key: 'SMAM', label: 'SMAM'},
      {key: 'CDP', label: 'CDP'},
      {key: 'Scheme_Score', label: 'Scheme Score'}
    ];
    
    machFields.forEach(function(f) {
      var val = isMatched ? props[f.key] : 'DATA NOT AVAILABLE';
      if (typeof val === 'number') val = val.toFixed(0);
      
      inspectorPanel.add(ui.Panel({
        widgets: [
          ui.Label(f.label + ':', {fontWeight: 'bold', fontSize: '12px', margin: '2px 0 0 0'}),
          ui.Label(String(val), {fontSize: '12px', color: isMatched ? '#4a5568' : '#a0aec0', margin: '2px 0 0 5px'})
        ], layout: ui.Panel.Layout.flow('horizontal')
      }));
    });
    
    // Decision Fields
    inspectorPanel.add(ui.Label('--- Decision Metrics ---', {color: 'gray', margin: '10px 0 5px 0'}));
    inspectorPanel.add(ui.Panel({
      widgets: [
        ui.Label('Policy Zone:', {fontWeight: 'bold', fontSize: '12px'}),
        ui.Label(props['Policy_Zon'] || 'N/A', {fontSize: '12px', margin: '0 0 0 5px'})
      ], layout: ui.Panel.Layout.flow('horizontal')
    }));
    inspectorPanel.add(ui.Panel({
      widgets: [
        ui.Label('Priority Index:', {fontWeight: 'bold', fontSize: '12px'}),
        ui.Label(props['Intervention_Priority'] ? String(props['Intervention_Priority']) + ' / 4' : 'N/A', {fontSize: '12px', margin: '0 0 0 5px', color: '#c53030'})
      ], layout: ui.Panel.Layout.flow('horizontal')
    }));
  });
});

Map.style().set('cursor', 'crosshair');

// ------------------------------------------------------------------------------
// 8. INITIALIZATION
// ------------------------------------------------------------------------------
ui.root.insert(0, mainPanel);
Map.setCenter(75.8, 30.9, 8); // Wall-to-wall Punjab
updateMapLayers();

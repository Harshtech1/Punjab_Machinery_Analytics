// ==============================================================================
// Punjab Government Decision Support Dashboard - V8 (Executive)
// Project: Punjab GeoMethane + Machinery Analytics
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. ASSET IMPORTS & PREPROCESSING
// ------------------------------------------------------------------------------
var ASSET_VILLAGES = 'projects/agrivision-38cc2/assets/punjab_machinery_ch4_shapefile'; 
var fc_villages = ee.FeatureCollection(ASSET_VILLAGES);

var mergedVillages = fc_villages.map(function(f) {
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
  f = f.set('Total_Mach', totalMachines); 
  
  var isMatched = ee.Algorithms.If(totalMachines.gt(0), 1, 0); 
  f = f.set('Is_Matched', isMatched);
  
  var ch4 = getNum('Pred_CH4');
  var ch4Class = ee.Algorithms.If(ch4.gt(1915), 'High', 
                 ee.Algorithms.If(ch4.gt(1900), 'Medium', 'Low'));
  f = f.set('CH4_Class', ch4Class);
  
  var ch4Score = ee.Algorithms.If(ch4.gt(1915), 3, ee.Algorithms.If(ch4.gt(1900), 2, ee.Algorithms.If(ch4.gt(1885), 1, 0)));
  
  var machScore = ee.Algorithms.If(ee.Number(isMatched).eq(0), 0, 
                  ee.Algorithms.If(totalMachines.lt(5), 2, 
                  ee.Algorithms.If(totalMachines.lt(15), 1, 0)));
                  
  var polScore = ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Policy Failure Zone'), 3, 0);
  
  var priority = ee.Number(ch4Score).add(ee.Number(machScore)).add(ee.Number(polScore));
  var finalPriority = ee.Algorithms.If(priority.gt(6), 4, 
                      ee.Algorithms.If(priority.gt(4), 3, 
                      ee.Algorithms.If(priority.gt(2), 2, 1))); 
                      
  return f.set('Intervention_Priority', finalPriority);
});

// Avoid "Description length exceeds maximum" by simplifying properties and using image paint
var districts = ee.FeatureCollection("FAO/GAUL/2015/level2")
                  .filter(ee.Filter.eq('ADM1_NAME', 'Punjab'))
                  .filterBounds(mergedVillages.geometry())
                  .map(function(f) { return ee.Feature(f.geometry(), {}); });

var districtBorders = ee.Image().paint(districts, 0, 1.5);
var villageOutlines = ee.Image().paint(mergedVillages, 0, 0.5);

var topPriorityPoints = mergedVillages.filter(ee.Filter.gte('Intervention_Priority', 4)).map(function(f) {
  return f.centroid();
});

// ------------------------------------------------------------------------------
// 2. VISUALIZATION PARAMETERS
// ------------------------------------------------------------------------------
var ch4Palette = ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b']; 
var machineryPalette = ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b'];
var schemeScorePalette = ['#ffffcc', '#fd8d3c', '#800026']; 

var visParams = {
  'Pred_CH4': {min: 1890, max: 1925, palette: ch4Palette}, 
  'In_Situ': {min: 0, max: 30, palette: machineryPalette},
  'Ex_Situ': {min: 0, max: 10, palette: machineryPalette},
  'Prime_Move': {min: 0, max: 15, palette: machineryPalette},
  'General': {min: 0, max: 15, palette: machineryPalette},
  'CRM': {min: 0, max: 15, palette: machineryPalette},
  'SMAM': {min: 0, max: 10, palette: machineryPalette},
  'CDP': {min: 0, max: 10, palette: machineryPalette},
  'Scheme_Score': {min: 0, max: 40, palette: schemeScorePalette},
  'Intervention_Priority': {min: 1, max: 4, palette: ['#1a9850', '#ffffbf', '#fd8d3c', '#d73027']}
};

var policyColors = {
  'Policy Failure Zone': '#d73027',        
  'Biomass Procurement Zone': '#1a9850',   
  'Intervention Success Zone': '#4575b4',  
  'Baseline Zone': '#e0f3f8',              
  'Unclassified': '#aaaaaa'
};

// ------------------------------------------------------------------------------
// 3. UI SETUP - LEFT PANEL (Navigation & Snapshot)
// ------------------------------------------------------------------------------
var leftPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {width: '320px', padding: '15px', backgroundColor: '#ffffff', border: '1px solid #cccccc'}
});

leftPanel.add(ui.Label({
  value: 'Punjab Methane Decision Support System',
  style: {fontWeight: 'bold', fontSize: '18px', color: '#1a365d', margin: '0 0 15px 0'}
}));

// Snapshot
var summaryPanel = ui.Panel({
  style: {padding: '10px', backgroundColor: '#f0f4f8', border: '1px solid #cbd5e0', margin: '0 0 20px 0'}
});
summaryPanel.add(ui.Label('Punjab Snapshot (2020)', {fontWeight: 'bold', fontSize: '14px', margin: '0 0 10px 0', color: '#2d3748'}));

var lblTotal = ui.Label('Villages Analyzed: Loading...', {margin: '4px 0', fontSize: '13px'});
var lblCoverage = ui.Label('Coverage Rate: Loading...', {margin: '4px 0', fontSize: '13px', fontWeight: 'bold'});
var lblHotspots = ui.Label('Methane Hotspots: Loading...', {margin: '4px 0', fontSize: '13px', color: '#c53030'});
var lblPriority = ui.Label('Top Priority Villages: Loading...', {margin: '4px 0', fontSize: '13px', color: '#d73027', fontWeight: 'bold'});

summaryPanel.add(lblTotal);
summaryPanel.add(lblCoverage);
summaryPanel.add(lblHotspots);
summaryPanel.add(lblPriority);
leftPanel.add(summaryPanel);

// Navigation
var toolsPanel = ui.Panel({
  style: {padding: '10px', backgroundColor: '#ffffff', border: '1px solid #e2e8f0'}
});
toolsPanel.add(ui.Label('Navigation', {fontWeight: 'bold', margin: '0 0 10px 0'}));

var districtSelect = ui.Select({
  items: ['Amritsar', 'Barnala', 'Bathinda', 'Faridkot', 'Fatehgarh Sahib', 'Fazilka', 'Firozpur', 'Gurdaspur', 'Hoshiarpur', 'Jalandhar', 'Kapurthala', 'Ludhiana', 'Mansa', 'Moga', 'Muktsar', 'Pathankot', 'Patiala', 'Rupnagar', 'Sangrur', 'SAS Nagar', 'SBS Nagar', 'Tarn Taran'],
  placeholder: 'District Dropdown...',
  onChange: function(dist) {
    var filtered = mergedVillages.filter(ee.Filter.eq('District', dist));
    Map.centerObject(filtered, 10);
    var style = ee.Image().paint(filtered, 0, 1.5);
    Map.layers().set(10, ui.Map.Layer(style, {palette: ['red']}, 'District Highlight'));
  },
  style: {stretch: 'horizontal'}
});
toolsPanel.add(districtSelect);

var villageSearch = ui.Textbox({
  placeholder: 'Village Search...',
  onChange: function(text) {
    var textUpper = text.toUpperCase();
    var filtered = mergedVillages.filter(ee.Filter.stringContains('Village_Na', textUpper));
    Map.centerObject(filtered, 14);
    var style = ee.Image().paint(filtered, 0, 3);
    Map.layers().set(11, ui.Map.Layer(style, {palette: ['blue']}, 'Village Highlight'));
  },
  style: {stretch: 'horizontal'}
});
toolsPanel.add(villageSearch);
leftPanel.add(toolsPanel);

// ------------------------------------------------------------------------------
// 4. RIGHT PANEL - THEMATIC LAYERS
// ------------------------------------------------------------------------------
var rightPanel = ui.Panel({
  style: {width: '280px', position: 'top-right', padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.95)'}
});

var activeLayerKey = 'Intervention_Priority';
var showTopPriority = false;
var showVillageBorders = false;
var showDistrictBorders = true;

function addSectionHeader(title) {
  rightPanel.add(ui.Label(title, {fontWeight: 'bold', fontSize: '13px', color: '#4a5568', margin: '15px 0 5px 0'}));
  rightPanel.add(ui.Label('━━━━━━━━━━━━━━━━━', {margin: '0 0 5px 0', color: '#e2e8f0'}));
}

function createLayerButton(label, key) {
  var isSpecial = (key === 'TOP_PRIORITY' || key === 'VILLAGE_BORDERS' || key === 'DISTRICT_BORDERS');
  return ui.Button({
    label: label,
    onClick: function() {
      if (key === 'TOP_PRIORITY') {
        showTopPriority = !showTopPriority;
      } else if (key === 'VILLAGE_BORDERS') {
        showVillageBorders = !showVillageBorders;
      } else if (key === 'DISTRICT_BORDERS') {
        showDistrictBorders = !showDistrictBorders;
      } else {
        activeLayerKey = key;
        updateLegend();
      }
      updateMapLayers();
    },
    style: {stretch: 'horizontal', margin: '2px 0'}
  });
}

// Base Map Controls
addSectionHeader('BASE MAP');
rightPanel.add(createLayerButton('District Boundaries', 'DISTRICT_BORDERS'));
rightPanel.add(createLayerButton('Village Boundaries', 'VILLAGE_BORDERS'));

addSectionHeader('METHANE');
rightPanel.add(createLayerButton('Methane Emissions', 'Pred_CH4'));

addSectionHeader('MACHINERY');
rightPanel.add(createLayerButton('In-Situ', 'In_Situ'));
rightPanel.add(createLayerButton('Ex-Situ', 'Ex_Situ'));
rightPanel.add(createLayerButton('Prime Movers', 'Prime_Move'));
rightPanel.add(createLayerButton('General', 'General'));

addSectionHeader('GOVERNMENT SCHEMES');
rightPanel.add(createLayerButton('CRM', 'CRM'));
rightPanel.add(createLayerButton('SMAM', 'SMAM'));
rightPanel.add(createLayerButton('CDP', 'CDP'));
rightPanel.add(createLayerButton('Scheme Score', 'Scheme_Score'));

addSectionHeader('DECISION SUPPORT');
rightPanel.add(createLayerButton('Policy Zones', 'Policy_Zon'));
rightPanel.add(createLayerButton('Priority Index', 'Intervention_Priority'));
rightPanel.add(createLayerButton('Top Priority Villages (Markers)', 'TOP_PRIORITY'));

Map.add(rightPanel);

// Disable native layer manager to use custom panel
Map.setControlVisibility({layerList: false});

// ------------------------------------------------------------------------------
// 5. MAP LAYER LOGIC
// ------------------------------------------------------------------------------
function updateMapLayers() {
  var key = activeLayerKey;
  var img;
  var vis = visParams[key];
  
  if (key === 'Policy_Zon') {
    img = mergedVillages.map(function(f) {
      var val = ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Policy Failure Zone'), 1,
                ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Biomass Procurement Zone'), 2,
                ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Intervention Success Zone'), 3, 
                ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Baseline Zone'), 4, 5)))); 
      return f.set('zone_val', val);
    }).reduceToImage(['zone_val'], ee.Reducer.first());
    
    vis = {
      min: 1, max: 5, 
      palette: [
        policyColors['Policy Failure Zone'], 
        policyColors['Biomass Procurement Zone'], 
        policyColors['Intervention Success Zone'], 
        policyColors['Baseline Zone'],
        policyColors['Unclassified']
      ]
    };
  } else {
    img = mergedVillages.reduceToImage([key], ee.Reducer.first());
    if (['In_Situ', 'Ex_Situ', 'Prime_Move', 'General', 'CRM', 'SMAM', 'CDP', 'Scheme_Score'].indexOf(key) > -1) {
       var mask = mergedVillages.reduceToImage(['Is_Matched'], ee.Reducer.first()).eq(1);
       img = img.updateMask(mask);
    }
  }
  
  Map.layers().set(0, ui.Map.Layer(img, vis, 'Thematic Fill', true));
  Map.layers().set(1, ui.Map.Layer(villageOutlines, {palette: ['#666666']}, 'Village Boundaries', showVillageBorders));
  Map.layers().set(2, ui.Map.Layer(districtBorders, {palette: ['black']}, 'District Boundaries', showDistrictBorders));
  
  if (showTopPriority) {
    var starStyle = topPriorityPoints.style({color: 'red', fillColor: 'red', pointShape: 'star', pointSize: 6});
    Map.layers().set(3, ui.Map.Layer(starStyle, {}, 'Top Priority Markers', true));
  } else {
    Map.layers().set(3, ui.Map.Layer(ee.Image(), {}, 'Top Priority Markers', false));
  }
}

// Auto-enable village borders on zoom > 11
Map.onChangeZoom(function(zoom) {
  if (!showVillageBorders && zoom > 11) {
    showVillageBorders = true;
    updateMapLayers();
  } else if (showVillageBorders && zoom <= 11) {
    showVillageBorders = false;
    updateMapLayers();
  }
});

// ------------------------------------------------------------------------------
// 6. DYNAMIC LEGEND
// ------------------------------------------------------------------------------
var legendPanel = ui.Panel({
  style: {position: 'bottom-left', padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.9)'}
});
Map.add(legendPanel);

function makeColorBarParams(palette) {
  return {
    bbox: '0,0,10,100',
    dimensions: '15x150',
    format: 'png',
    min: 0,
    max: 1,
    palette: palette
  };
}

function updateLegend() {
  legendPanel.clear();
  var key = activeLayerKey;
  
  legendPanel.add(ui.Label('Legend: ' + key, {fontWeight: 'bold', margin: '0 0 10px 0'}));
  
  if (key === 'Policy_Zon') {
    for (var zone in policyColors) {
      var colorBox = ui.Label('', {backgroundColor: policyColors[zone], padding: '8px', margin: '0 0 4px 0'});
      var desc = ui.Label(zone, {margin: '0 0 4px 8px', fontSize: '12px'});
      legendPanel.add(ui.Panel([colorBox, desc], ui.Panel.Layout.Flow('horizontal')));
    }
    return;
  }
  
  var vis = visParams[key];
  if (!vis || !vis.palette) return;
  
  var colorBar = ui.Thumbnail({
    image: ee.Image.pixelLonLat().select(1),
    params: makeColorBarParams(vis.palette),
    style: {stretch: 'vertical', margin: '0 8px 0 0', maxHeight: '150px'}
  });
  
  var minLbl = (key === 'Pred_CH4') ? 'P5 (' + Math.round(vis.min) + ')' : vis.min;
  var maxLbl = (key === 'Pred_CH4') ? 'P95 (' + Math.round(vis.max) + ')' : vis.max;
  
  var labels = ui.Panel({
    widgets: [
      ui.Label(maxLbl, {margin: '0 0 0 0', fontSize: '12px'}),
      ui.Label('', {margin: 'auto 0', stretch: 'vertical'}), 
      ui.Label(minLbl, {margin: '0 0 0 0', fontSize: '12px'})
    ],
    layout: ui.Panel.Layout.flow('vertical'),
    style: {stretch: 'vertical'}
  });
  
  legendPanel.add(ui.Panel([colorBar, labels], ui.Panel.Layout.Flow('horizontal')));
}

// ------------------------------------------------------------------------------
// 7. VILLAGE PROFILE CARD (Government Briefing Layout)
// ------------------------------------------------------------------------------
var inspectorPanel = ui.Panel({
  style: {width: '340px', padding: '15px', position: 'bottom-right', shown: false, backgroundColor: '#ffffff', border: '1px solid #2b6cb0'}
});
Map.add(inspectorPanel);

function addProfileDivider(panel) {
  panel.add(ui.Label('━━━━━━━━━━━━━━━━━━━━━━', {margin: '8px 0', color: '#cbd5e0', fontSize: '12px', textAlign: 'center', stretch: 'horizontal'}));
}

function addRow(panel, label, value, valColor, valBold) {
  panel.add(ui.Panel({
    widgets: [
      ui.Label(label, {fontSize: '13px', color: '#4a5568', margin: '2px 0', stretch: 'horizontal'}),
      ui.Label(String(value), {fontSize: '13px', color: valColor || '#1a202c', fontWeight: valBold ? 'bold' : 'normal', margin: '2px 0', textAlign: 'right'})
    ],
    layout: ui.Panel.Layout.flow('horizontal'),
    style: {stretch: 'horizontal'}
  }));
}

Map.onClick(function(coords) {
  inspectorPanel.clear();
  inspectorPanel.style().set('shown', true);
  inspectorPanel.add(ui.Label('Loading official data...', {color: 'gray', fontStyle: 'italic'}));
  
  var point = ee.Geometry.Point(coords.lon, coords.lat);
  var clickedFeature = mergedVillages.filterBounds(point).first();
  
  clickedFeature.evaluate(function(feature) {
    inspectorPanel.clear();
    
    if (!feature) {
      inspectorPanel.add(ui.Label('No village found at this location.', {color: '#c53030'}));
      inspectorPanel.add(ui.Button('Close', function() { inspectorPanel.style().set('shown', false); }));
      return;
    }
    
    var props = feature.properties;
    var isMatched = props['Is_Matched'] === 1;
    var closeBtn = ui.Button('X', function() { inspectorPanel.style().set('shown', false); }, false, {position: 'top-right', margin: '0', padding: '0'});
    inspectorPanel.add(closeBtn);
    
    inspectorPanel.add(ui.Label('VILLAGE PROFILE', {fontWeight: 'bold', fontSize: '16px', color: '#2b6cb0', textAlign: 'center', stretch: 'horizontal', margin: '0 0 5px 0'}));
    
    // SECTION 1: Location
    addRow(inspectorPanel, 'Village', props['Village_Na'] || 'Unknown', '#1a365d', true);
    addRow(inspectorPanel, 'District', props['District'] || 'Unknown', '#1a365d', true);
    
    addProfileDivider(inspectorPanel);
    
    // SECTION 2: Methane Status
    inspectorPanel.add(ui.Label('METHANE STATUS', {fontWeight: 'bold', fontSize: '12px', color: '#718096'}));
    var ch4Val = props['Pred_CH4'] ? props['Pred_CH4'].toFixed(2) + ' ppb' : 'N/A';
    var ch4Class = props['CH4_Class'] || 'Unknown';
    var ch4Color = (ch4Class === 'High') ? '#c53030' : ((ch4Class === 'Medium') ? '#dd6b20' : '#2f855a');
    
    addRow(inspectorPanel, 'Predicted CH4', ch4Val, '#1a202c', true);
    addRow(inspectorPanel, 'Classification', ch4Class.toUpperCase(), ch4Color, true);
    
    addProfileDivider(inspectorPanel);
    
    // SECTION 3: Machinery
    inspectorPanel.add(ui.Label('MACHINERY', {fontWeight: 'bold', fontSize: '12px', color: '#718096'}));
    var vC = isMatched ? '#1a202c' : '#a0aec0';
    var noDataStr = 'NO DATA';
    addRow(inspectorPanel, 'In-Situ', isMatched ? props['In_Situ'] : noDataStr, vC);
    addRow(inspectorPanel, 'Ex-Situ', isMatched ? props['Ex_Situ'] : noDataStr, vC);
    addRow(inspectorPanel, 'Prime Mover', isMatched ? props['Prime_Move'] : noDataStr, vC);
    addRow(inspectorPanel, 'General', isMatched ? props['General'] : noDataStr, vC);
    
    addProfileDivider(inspectorPanel);
    
    // SECTION 4: Schemes
    inspectorPanel.add(ui.Label('GOVERNMENT SCHEMES', {fontWeight: 'bold', fontSize: '12px', color: '#718096'}));
    addRow(inspectorPanel, 'CRM', isMatched ? props['CRM'] : noDataStr, vC);
    addRow(inspectorPanel, 'SMAM', isMatched ? props['SMAM'] : noDataStr, vC);
    addRow(inspectorPanel, 'CDP', isMatched ? props['CDP'] : noDataStr, vC);
    addRow(inspectorPanel, 'Scheme Score', isMatched ? props['Scheme_Score'] : noDataStr, vC, true);
    
    addProfileDivider(inspectorPanel);
    
    // SECTION 5: Decision Support
    inspectorPanel.add(ui.Label('DECISION SUPPORT', {fontWeight: 'bold', fontSize: '12px', color: '#718096'}));
    var polZone = props['Policy_Zon'] || 'Unclassified';
    addRow(inspectorPanel, 'Policy Zone', polZone, '#1a365d', true);
    
    var priIdx = props['Intervention_Priority'] ? String(props['Intervention_Priority']) + ' / 4' : 'N/A';
    addRow(inspectorPanel, 'Priority Index', priIdx, '#c53030', true);
  });
});

Map.style().set('cursor', 'crosshair');

// ------------------------------------------------------------------------------
// 8. ASYNC INITIALIZATION & MAP SETUP
// ------------------------------------------------------------------------------
ui.root.insert(0, leftPanel);
Map.setCenter(75.8, 30.9, 8); 

// Populate snapshot stats asynchronously
var numVillages = mergedVillages.size();
var numMatched = mergedVillages.filter(ee.Filter.gt('Total_Mach', 0)).size();
var numHotspots = mergedVillages.filter(ee.Filter.gt('Pred_CH4', 1912)).size(); 
var numPriority = mergedVillages.filter(ee.Filter.gte('Intervention_Priority', 4)).size();

ee.Dictionary({
  total: numVillages,
  matched: numMatched,
  hotspots: numHotspots,
  priority: numPriority
}).evaluate(function(res) {
  lblTotal.setValue('Villages Analyzed: ' + res.total.toLocaleString());
  var cov = ((res.matched / res.total) * 100).toFixed(1);
  lblCoverage.setValue('Coverage Rate: ' + cov + '%');
  lblHotspots.setValue('Methane Hotspots: ' + res.hotspots.toLocaleString());
  lblPriority.setValue('Top Priority Villages: ' + res.priority.toLocaleString());
});

// Dynamic Methane Scaling
mergedVillages.reduceColumns({
  reducer: ee.Reducer.percentile([5, 95]),
  selectors: ['Pred_CH4']
}).evaluate(function(res) {
  if (res && res.p5 && res.p95) {
    visParams['Pred_CH4'].min = res.p5;
    visParams['Pred_CH4'].max = res.p95;
    if (activeLayerKey === 'Pred_CH4') {
      updateMapLayers();
      updateLegend();
    }
  }
});

updateMapLayers();
updateLegend();

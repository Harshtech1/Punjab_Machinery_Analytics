// ==============================================================================
// Punjab Government Decision Support Dashboard - V6 (Executive)
// Project: Punjab GeoMethane + Machinery Analytics
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. ASSET IMPORTS
// ------------------------------------------------------------------------------
var ASSET_VILLAGES = 'projects/agrivision-38cc2/assets/punjab_machinery_ch4_shapefile'; 

var fc_villages = ee.FeatureCollection(ASSET_VILLAGES);

// Base machinery logic
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

// Districts for boundaries and labels
var districts = ee.FeatureCollection("FAO/GAUL/2015/level2")
                  .filter(ee.Filter.eq('ADM1_NAME', 'Punjab'))
                  .filterBounds(mergedVillages.geometry());

// ------------------------------------------------------------------------------
// 2. VISUALIZATION PARAMETERS
// ------------------------------------------------------------------------------
// Scientific methane palette (P5-P95 dynamically updated later, initially fallback)
var ch4Palette = ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b']; 
var machineryPalette = ['#f7fbff', '#c6dbef', '#6baed6', '#2171b5', '#08306b'];
var schemeScorePalette = ['#ffffcc', '#fd8d3c', '#800026']; 

var visParams = {
  'Pred_CH4': {min: 1890, max: 1925, palette: ch4Palette}, // Will be overridden by P5/P95
  'In_Situ': {min: 0, max: 30, palette: machineryPalette},
  'Ex_Situ': {min: 0, max: 10, palette: machineryPalette},
  'Prime_Move': {min: 0, max: 15, palette: machineryPalette},
  'General': {min: 0, max: 15, palette: machineryPalette},
  'Scheme_Score': {min: 0, max: 40, palette: schemeScorePalette},
  'Is_Matched': {min: 0, max: 1, palette: ['#a0aec0', '#48bb78']}, 
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
// 3. UI SETUP - MAIN PANEL
// ------------------------------------------------------------------------------
var mainPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {width: '420px', padding: '15px', backgroundColor: '#ffffff', border: '1px solid #cccccc'}
});

mainPanel.add(ui.Label({
  value: 'Punjab Village Methane & Agricultural Machinery Decision Support Dashboard',
  style: {fontWeight: 'bold', fontSize: '20px', color: '#1a365d', textAlign: 'center', margin: '0 0 15px 0'}
}));

mainPanel.add(ui.Label({
  value: 'Official Executive Dashboard for Punjab Agriculture Department.',
  style: {fontSize: '12px', color: '#718096', margin: '0 0 20px 0', textAlign: 'center'}
}));

// ------------------------------------------------------------------------------
// 4. PUNJAB SNAPSHOT (EXECUTIVE PANEL)
// ------------------------------------------------------------------------------
var summaryPanel = ui.Panel({
  style: {padding: '10px', backgroundColor: '#f0f4f8', border: '1px solid #cbd5e0', margin: '0 0 15px 0'}
});
summaryPanel.add(ui.Label('Punjab Snapshot (2020)', {fontWeight: 'bold', fontSize: '15px', margin: '0 0 10px 0', color: '#2d3748'}));

var lblTotal = ui.Label('Villages Analyzed: Loading...', {margin: '2px 0 2px 0', fontSize: '13px'});
var lblMatched = ui.Label('Verified Machinery Villages: Loading...', {margin: '2px 0 2px 0', fontSize: '13px'});
var lblCoverage = ui.Label('Coverage Rate: Loading...', {margin: '2px 0 2px 0', fontSize: '13px', fontWeight: 'bold'});
var lblHotspots = ui.Label('Methane Hotspots: Loading...', {margin: '2px 0 2px 0', fontSize: '13px', color: '#c53030'});
var lblPriority = ui.Label('Top Priority Villages: Loading...', {margin: '2px 0 2px 0', fontSize: '13px', color: '#d73027', fontWeight: 'bold'});

summaryPanel.add(lblTotal);
summaryPanel.add(lblMatched);
summaryPanel.add(lblCoverage);
summaryPanel.add(lblHotspots);
summaryPanel.add(lblPriority);
mainPanel.add(summaryPanel);

// Async calculations
var numVillages = mergedVillages.size();
var numMatched = mergedVillages.filter(ee.Filter.gt('Total_Mach', 0)).size();
var numHotspots = mergedVillages.filter(ee.Filter.gt('Pred_CH4', 1912)).size(); // Or use P95 dynamically
var numPriority = mergedVillages.filter(ee.Filter.gte('Intervention_Priority', 4)).size();

ee.Dictionary({
  total: numVillages,
  matched: numMatched,
  hotspots: numHotspots,
  priority: numPriority
}).evaluate(function(res) {
  lblTotal.setValue('Villages Analyzed: ' + res.total.toLocaleString());
  lblMatched.setValue('Verified Machinery Villages: ' + res.matched.toLocaleString());
  var cov = ((res.matched / res.total) * 100).toFixed(1);
  lblCoverage.setValue('Coverage Rate: ' + cov + '%');
  lblHotspots.setValue('Methane Hotspots: ' + res.hotspots.toLocaleString());
  lblPriority.setValue('Top Priority Villages: ' + res.priority.toLocaleString());
});

// Calculate P5-P95 for Methane dynamically
mergedVillages.reduceColumns({
  reducer: ee.Reducer.percentile([5, 95]),
  selectors: ['Pred_CH4']
}).evaluate(function(res) {
  if (res && res.p5 && res.p95) {
    visParams['Pred_CH4'].min = res.p5;
    visParams['Pred_CH4'].max = res.p95;
    if (activeLayerKey === 'Pred_CH4') updateMapLayers();
  }
});

// ------------------------------------------------------------------------------
// 5. SINGLE LAYER SELECTOR
// ------------------------------------------------------------------------------
var activeLayerKey = 'Intervention_Priority';

var thematicLayersMap = {
  'Intervention Priority Index': 'Intervention_Priority',
  'Methane Emissions': 'Pred_CH4',
  'In-Situ Machinery': 'In_Situ',
  'Ex-Situ Machinery': 'Ex_Situ',
  'Prime Movers': 'Prime_Move',
  'General Machinery': 'General',
  'CRM': 'CRM',
  'SMAM': 'SMAM',
  'CDP': 'CDP',
  'Scheme Score': 'Scheme_Score',
  'Data Quality': 'Is_Matched',
  'Policy Zones': 'Policy_Zon'
};

var layerSelect = ui.Select({
  items: Object.keys(thematicLayersMap),
  value: 'Intervention Priority Index',
  onChange: function(selected) {
    activeLayerKey = thematicLayersMap[selected];
    updateMapLayers();
    updateLegend();
  },
  style: {stretch: 'horizontal', margin: '10px 0 20px 0'}
});

mainPanel.add(ui.Label('Display Layer:', {fontWeight: 'bold', fontSize: '14px'}));
mainPanel.add(layerSelect);

// ------------------------------------------------------------------------------
// 6. MAP LAYER UPDATES
// ------------------------------------------------------------------------------

// Add permanent base layers ONCE
var villageOutlines = mergedVillages.style({
  color: '666666',
  fillColor: '00000000',
  width: 0.3
});

var districtBorders = districts.style({
  color: 'black',
  fillColor: '00000000',
  width: 1.5
});

Map.layers().set(0, ui.Map.Layer(villageOutlines, {}, 'Village Boundaries', true));
Map.layers().set(1, ui.Map.Layer(districtBorders, {}, 'District Boundaries', true));

// District Labels via Gena's package
try {
  var text = require('users/gena/packages:text');
  var labelsLayer = districts.map(function(feat) {
    return text.draw(feat.get('ADM2_NAME'), feat.centroid(10), Map.getScale() || 2000, {
      fontSize: 14, textColor: 'black', outlineColor: 'white', outlineWidth: 2
    });
  });
  var labelsImage = ee.ImageCollection(labelsLayer).mosaic();
  Map.layers().set(2, ui.Map.Layer(labelsImage, {}, 'District Labels', true));
} catch(e) {
  print("Note: Gena's text package not accessible. Skipping district labels on map.");
}

// Function to update the thematic layer
function updateMapLayers() {
  // Clear only the thematic layer (index 3) and district highlight (index 4/5) if we want to reset
  // We will place thematic layer at index 0, behind the outlines!
  // Actually, wait, outlines are at 1 and 2, thematic should be at 0.
  
  var key = activeLayerKey;
  var img;
  var vis = visParams[key];
  
  if (key === 'Policy_Zon') {
    img = mergedVillages.map(function(f) {
      var val = ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Policy Failure Zone'), 1,
                ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Biomass Procurement Zone'), 2,
                ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Intervention Success Zone'), 3, 
                ee.Algorithms.If(ee.Filter.eq('Policy_Zon', 'Baseline Zone'), 4, 5)))); // 5 for Unclassified
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
    if (['In_Situ', 'Ex_Situ', 'Prime_Move', 'General', 'Scheme_Score'].indexOf(key) > -1) {
       var mask = mergedVillages.reduceToImage(['Is_Matched'], ee.Reducer.first()).eq(1);
       img = img.updateMask(mask);
    }
  }
  
  // Set the thematic fill at index 0 (bottom layer)
  Map.layers().set(0, ui.Map.Layer(img, vis, 'Thematic Fill: ' + key, true));
  
  // Re-assert outlines on top (indexes 1, 2, 3)
  Map.layers().set(1, ui.Map.Layer(villageOutlines, {}, 'Village Boundaries', true));
  Map.layers().set(2, ui.Map.Layer(districtBorders, {}, 'District Boundaries', true));
}

// ------------------------------------------------------------------------------
// 7. DYNAMIC LEGEND
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
  
  var title = Object.keys(thematicLayersMap).find(function(k) { return thematicLayersMap[k] === key; });
  legendPanel.add(ui.Label(title + ' Legend', {fontWeight: 'bold', margin: '0 0 10px 0'}));
  
  if (key === 'Policy_Zon') {
    Object.keys(policyColors).forEach(function(zone) {
      var colorBox = ui.Label('', {backgroundColor: policyColors[zone], padding: '8px', margin: '0 0 4px 0'});
      var desc = ui.Label(zone, {margin: '0 0 4px 8px', fontSize: '12px'});
      legendPanel.add(ui.Panel([colorBox, desc], ui.Panel.Layout.Flow('horizontal')));
    });
    return;
  }
  
  if (key === 'Is_Matched') {
     var c1 = ui.Label('', {backgroundColor: '#48bb78', padding: '8px', margin: '0 0 4px 0'});
     var d1 = ui.Label('Data Available', {margin: '0 0 4px 8px', fontSize: '12px'});
     var c2 = ui.Label('', {backgroundColor: '#a0aec0', padding: '8px', margin: '0 0 4px 0'});
     var d2 = ui.Label('No Data', {margin: '0 0 4px 8px', fontSize: '12px'});
     legendPanel.add(ui.Panel([c1, d1], ui.Panel.Layout.Flow('horizontal')));
     legendPanel.add(ui.Panel([c2, d2], ui.Panel.Layout.Flow('horizontal')));
     return;
  }
  
  // Continuous Colorbar Legend
  var vis = visParams[key];
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
// 8. SEARCH, FILTER & NAVIGATION
// ------------------------------------------------------------------------------
var toolsPanel = ui.Panel({
  style: {padding: '10px', backgroundColor: '#f9f9f9', border: '1px solid #e2e8f0', margin: '15px 0 0 0'}
});
toolsPanel.add(ui.Label('District Navigation', {fontWeight: 'bold', margin: '0 0 10px 0'}));

var districtSelect = ui.Select({
  items: ['Amritsar', 'Barnala', 'Bathinda', 'Faridkot', 'Fatehgarh Sahib', 'Fazilka', 'Firozpur', 'Gurdaspur', 'Hoshiarpur', 'Jalandhar', 'Kapurthala', 'Ludhiana', 'Mansa', 'Moga', 'Muktsar', 'Pathankot', 'Patiala', 'Rupnagar', 'Sangrur', 'SAS Nagar', 'SBS Nagar', 'Tarn Taran'],
  placeholder: 'Select District...',
  onChange: function(dist) {
    var filtered = mergedVillages.filter(ee.Filter.eq('District', dist));
    Map.centerObject(filtered, 10);
    // V6 Fix: thin outline, no fill
    var style = filtered.style({color: 'red', fillColor: '00000000', width: 0.5});
    Map.layers().set(10, ui.Map.Layer(style, {}, 'District Highlight'));
  }
});
toolsPanel.add(districtSelect);
mainPanel.add(toolsPanel);

// ------------------------------------------------------------------------------
// 9. MAP CLICK POPUP
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
    var clBtn = ui.Button('X', function() { inspectorPanel.style().set('shown', false); });
    closeRow.add(clBtn);
    inspectorPanel.add(closeRow);
    
    if (!isMatched) {
       inspectorPanel.add(ui.Label('Machinery Status: DATA NOT AVAILABLE', {color: '#c53030', fontWeight: 'bold', margin: '5px 0 10px 0'}));
    } else {
       inspectorPanel.add(ui.Label('Machinery Status: VERIFIED', {color: '#2f855a', fontWeight: 'bold', margin: '5px 0 10px 0'}));
    }
    
    var ch4Val = props['Pred_CH4'];
    inspectorPanel.add(ui.Panel({
      widgets: [
        ui.Label('Predicted CH4:', {fontWeight: 'bold', fontSize: '13px'}),
        ui.Label((ch4Val ? ch4Val.toFixed(2) : 'N/A') + ' ppb', {fontSize: '13px', margin: '0 0 0 5px'})
      ], layout: ui.Panel.Layout.flow('horizontal')
    }));
    
    var machFields = [
      {key: 'In_Situ', label: 'In-Situ'},
      {key: 'Ex_Situ', label: 'Ex-Situ'},
      {key: 'Prime_Move', label: 'Prime Mover'},
      {key: 'General', label: 'General'},
      {key: 'CRM', label: 'CRM'},
      {key: 'SMAM', label: 'SMAM'},
      {key: 'CDP', label: 'CDP'}
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
    
    inspectorPanel.add(ui.Label('--- Decision Metrics ---', {color: 'gray', margin: '10px 0 5px 0'}));
    inspectorPanel.add(ui.Panel({
      widgets: [
        ui.Label('Policy Zone:', {fontWeight: 'bold', fontSize: '12px'}),
        ui.Label(props['Policy_Zon'] || 'Unclassified', {fontSize: '12px', margin: '0 0 0 5px'})
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
// 10. INITIALIZATION
// ------------------------------------------------------------------------------
ui.root.insert(0, mainPanel);
Map.setCenter(75.8, 30.9, 8); 
updateMapLayers();
updateLegend();

/**
 * Water Balance Suitability Assessment for AWD (Alternate Wetting and Drying)
 * 
 * This script computes dekad-level water balance using satellite data and
 * evaluates AWD suitability across multiple water deficit thresholds.
 * 
 * Key Components:
 * 1. Dekad rainfall aggregation from CHIRPS daily data
 * 2. 8-day PET from MODIS MOD16A2 aligned to dekad calendar
 * 3. Soil percolation from SoilGrids texture classification
 * 4. Water balance computation: Rain - (PET + Percolation)
 * 5. Threshold sensitivity analysis across 7 deficit levels
 * 6. AWD suitability classification (High/Moderate/Low)
 * 
 * Output: Multi-band image with suitability for each threshold
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

var config = {
  year: 2022,
  seasonStartDekad: 10,
  seasonEndDekad: 28,
  excludeFirstDekads: 2,
  excludeLastDekads: 1,
  riceScale: 500,  // meters
  minRainfallThreshold: 5.0,  // mm - supplemental irrigation trigger
  deficitThresholds: [-25, -50, -70, -90, -110, -130, -150],  // mm (negative)
  project: 'ee-mytransatellite',
  exportBucket: 'AWD'
};

// ============================================================================
// STUDY AREA SETUP
// ============================================================================

// Load rice extent map
var riceMap = ee.Image("projects/ee-mytransatellite/assets/Rice-JPN-2023-v1");
var riceMasked = riceMap.updateMask(riceMap.eq(1));
var riceAOI = riceMasked.geometry();

Map.centerObject(riceAOI, 8);

// Upscale rice to target resolution and create mask
var rice500m = riceMasked
  .reduceResolution({reducer: ee.Reducer.mode(), maxPixels: 65535})
  .reproject({crs: 'EPSG:4326', scale: config.riceScale})
  .clip(riceAOI)
  .rename('RiceExtent_500m');

var riceMask500m = rice500m.neq(0);

// ============================================================================
// DATA ACQUISITION FUNCTIONS
// ============================================================================

/**
 * Prepare a layer to common resolution and projection
 */
function prepareLayer(image, isCategorical) {
  var prepared;
  if (isCategorical) {
    prepared = image
      .reduceResolution({reducer: ee.Reducer.mode(), maxPixels: 65535})
      .clip(riceAOI)
      .reproject({crs: 'EPSG:4326', scale: config.riceScale});
  } else {
    prepared = image
      .resample('bilinear')
      .clip(riceAOI)
      .reproject({crs: 'EPSG:4326', scale: config.riceScale});
  }
  return prepared.updateMask(riceMask500m);
}

/**
 * Generate dekad dates for a given year
 */
function generateDekads(year) {
  var start = ee.Date.fromYMD(year, 1, 1);
  return ee.List.sequence(0, 35).map(function(d) {
    return start.advance(ee.Number(d).multiply(10), 'day');
  });
}

/**
 * Sum daily CHIRPS rainfall to dekad totals
 */
function sumRainfallForDekad(startDate) {
  var start = ee.Date(startDate);
  var end = start.advance(10, 'day');
  var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY');
  var sumImg = chirps.filterDate(start, end).sum().toFloat();
  return prepareLayer(sumImg, false).rename('Rain_mm_dekad').set('system:time_start', start.millis());
}

/**
 * Compute PET for a dekad using weighted overlap of 8-day MODIS MOD16A2 tiles
 */
function computeDekadPET(startDate) {
  var start = ee.Date(startDate);
  var end = start.advance(10, 'day');
  var modPET = ee.ImageCollection('MODIS/061/MOD16A2').select('PET').filterBounds(riceAOI);
  
  var candidates = modPET.filterDate(start.advance(-8, 'day'), end);
  
  var weighted = candidates.map(function(img) {
    var imgStart = ee.Date(img.get('system:time_start'));
    var imgEnd = imgStart.advance(8, 'day');
    
    var overlapStart = ee.Date(imgStart.millis().max(start.millis()));
    var overlapEnd = ee.Date(imgEnd.millis().min(end.millis()));
    var overlapDays = overlapEnd.difference(overlapStart, 'day').max(0);
    
    var scaled = img.select('PET')
      .multiply(0.1)  // scale factor to mm per 8 days
      .multiply(overlapDays.divide(8.0))  // weight by overlap
      .toFloat();
    
    return scaled.rename('PET_part');
  });
  
  var petSum = ee.ImageCollection(weighted).sum().unmask(0).toFloat();
  return prepareLayer(ee.Image(petSum), false).rename('PET_mm_dekad').set('system:time_start', start.millis());
}

// ============================================================================
// SOIL PERCOLATION FROM SOILGRIDS
// ============================================================================

/**
 * Classify soil texture and assign percolation rate
 */
function computePercolationRate() {
  var clay = ee.Image("projects/soilgrids-isric/clay_mean")
    .select('clay_0-5cm_mean').divide(10).toFloat();  // convert to %
  var sand = ee.Image("projects/soilgrids-isric/sand_mean")
    .select('sand_0-5cm_mean').divide(10).toFloat();
  
  var tc = ee.Image(0);  // texture class
  
  // Mutually exclusive classification
  var cond1 = clay.gte(45);
  tc = tc.where(cond1.and(tc.eq(0)), 1);  // heavy clay
  
  var cond2 = clay.gte(20).and(clay.lt(45)).and(sand.lte(52));
  tc = tc.where(cond2.and(tc.eq(0)), 2);  // clay loam
  
  var cond3 = clay.gte(20).and(clay.lt(35)).and(sand.gt(52));
  tc = tc.where(cond3.and(tc.eq(0)), 3);  // sandy clay loam
  
  tc = tc.where(tc.eq(0), 4);  // default class
  
  // Percolation rates (mm/day) → convert to dekad (/10)
  var potPc = tc.remap(
    [1, 2, 3, 4],  // soil classes
    [3.0, 4.0, 9.0, 12.0]  // mm/day percolation
  ).multiply(10.0).toFloat();  // convert to dekad totals
  
  return prepareLayer(ee.Image(potPc), true).rename('PotPc_mm_dekad');
}

// ============================================================================
// WATER BALANCE & AWD SUITABILITY
// ============================================================================

/**
 * Apply supplemental irrigation where rainfall < threshold
 */
function addMinimumIrrigation(rainImg) {
  return rainImg.expression(
    'rain < threshold ? threshold : rain',
    {'rain': rainImg, 'threshold': config.minRainfallThreshold}
  ).rename('Rain_with_Irr');
}

/**
 * Compute suitability for a single deficit threshold
 */
var calculateSuitability = function(deficitThreshold) {
  var activeStart = config.seasonStartDekad + config.excludeFirstDekads;
  var activeEnd = config.seasonEndDekad - config.excludeLastDekads;
  var activeDekadIndices = ee.List.sequence(activeStart, activeEnd);
  
  // Compute water balance for active season dekads
  var waterBalanceList = activeDekadIndices.map(function(idx) {
    var d = ee.Number(idx);
    var rainWithIrr = ee.Image(dekadRainWithIrrCollection.toList(dekadRainWithIrrCollection.size()).get(idx));
    var pet = ee.Image(dekadPET.toList(36).get(idx));
    var wb = rainWithIrr.subtract(pet).subtract(potPcFinal)
      .rename('WaterBalance')
      .updateMask(riceMask500m)
      .set('system:time_start', pet.get('system:time_start'));
    return wb;
  });
  
  var waterBalanceCollection = ee.ImageCollection.fromImages(waterBalanceList);
  
  // Assess suitability: WB < 0 (dries) AND WB >= threshold (not too dry)
  var suitableDekadCollection = waterBalanceCollection.map(function(img) {
    return img.lt(0).and(img.gte(ee.Number(deficitThreshold)))
      .rename('SuitableDekad')
      .toFloat();
  });
  
  // Fraction of suitable dekads in active season
  var numValidDekads = suitableDekadCollection.map(function(img){
    return img.mask().unmask(0);
  }).sum();
  
  var fractionSuitable = suitableDekadCollection.sum()
    .divide(numValidDekads)
    .clip(riceAOI)
    .updateMask(riceMask500m)
    .toFloat();
  
  // Classify: 3=High (≥66%), 2=Moderate (33-66%), 1=Low (<33%)
  var suitability = ee.Image(0)
    .where(fractionSuitable.gte(0.66), 3)
    .where(fractionSuitable.gte(0.33).and(fractionSuitable.lt(0.66)), 2)
    .where(fractionSuitable.lt(0.33), 1)
    .clip(riceAOI)
    .updateMask(riceMask500m)
    .toInt8();
  
  var bandName = ee.String('suitability_').cat(ee.Number(deficitThreshold).format('%d'));
  return suitability.rename(bandName);
};

// ============================================================================
// MAIN PIPELINE EXECUTION
// ============================================================================

// Generate dekad dates
var dekads = generateDekads(config.year);

// Compute rainfall dekads
var dekadRainfall = ee.ImageCollection(dekads.map(sumRainfallForDekad));

// Compute PET dekads
var dekadPET = ee.ImageCollection(
  dekads.map(computeDekadPET)
);

// Compute percolation
var potPcFinal = computePercolationRate();

// Apply minimum irrigation threshold to rainfall
var activeIndices = ee.List.sequence(
  config.seasonStartDekad + config.excludeFirstDekads,
  config.seasonEndDekad - config.excludeLastDekads
);

var dekadRainWithIrrList = activeIndices.map(function(idx) {
  var rainImg = ee.Image(dekadRainfall.toList(36).get(idx));
  return addMinimumIrrigation(rainImg).set('system:time_start', rainImg.get('system:time_start'));
});
var dekadRainWithIrrCollection = ee.ImageCollection.fromImages(dekadRainWithIrrList);

// Compute suitability for each threshold
var suitabilityImagesList = ee.List(config.deficitThresholds).map(calculateSuitability);
var suitabilityCollection = ee.ImageCollection.fromImages(suitabilityImagesList);
var finalImage = suitabilityCollection.toBands();

// ============================================================================
// VISUALIZATION
// ============================================================================

Map.addLayer(
  finalImage.select('0_suitability_-50'),
  {min: 1, max: 3, palette: ['red', 'yellow', 'green']},
  'AWD Suitability (-50mm threshold)'
);

// ============================================================================
// EXPORT
// ============================================================================

Export.image.toDrive({
  image: finalImage.toInt8(),
  description: 'Japan_AWD_Suitability_All_Thresholds_' + config.year,
  folder: config.exportBucket,
  fileNamePrefix: 'Japan_AWD_Suitability_All_Thresholds',
  region: riceAOI,
  scale: config.riceScale,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

print('Export started. Check Google Drive for output in folder:', config.exportBucket);
print('Final image bands:', finalImage.bandNames());

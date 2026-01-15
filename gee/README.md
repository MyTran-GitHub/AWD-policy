# Google Earth Engine Setup Guide

## Overview

This directory contains the Google Earth Engine JavaScript code for satellite-based water balance computation and AWD suitability assessment. The script processes CHIRPS rainfall, MODIS evapotranspiration, and SoilGrids soil data to produce dekad-level (10-day) water balance maps.

## Prerequisites

1. **Google Earth Engine Account**: Sign up at [https://earthengine.google.com/](https://earthengine.google.com/)
2. **Google Drive Account**: For storing exported results
3. **Study Area Assets**: Define rice extent boundaries (see "Preparing Study Area Data" below)

## Quick Start

### 1. Open Script in GEE Editor

1. Go to [Google Earth Engine Code Editor](https://code.earthengine.google.com/)
2. Create a new script and copy the contents of `water_balance_suitability.js`
3. Or import the shared script (coming soon)

### 2. Configure Study Area

At the top of the script, modify the configuration block:

```javascript
// CONFIGURATION
var CONFIG = {
  year: 2022,  // Analysis year
  season: {dekad_start: 10, dekad_end: 28},  // Season (dekad 10-28 = May-Sep)
  exclusion_windows: {exclude_first: 2, exclude_last: 1},  // Exclude establishment/harvest phases
  deficit_thresholds: [-25, -50, -70, -90, -110, -130, -150],  // Deficit thresholds (mm)
  irrigation_threshold: 5.0,  // Min rainfall threshold (mm)
  output_scale: 500,  // Output resolution (meters)
  max_pixels: 1e13  // Max processing area
};

// STUDY AREA (replace with your rice extent)
var rice_map = ee.Image("users/your-username/japan_rice_2020");
```

### 3. Load Study Area Data

**Option A: Use User Asset (Recommended)**

If you have a pre-processed rice extent map:

```javascript
var rice_map = ee.Image("users/[your-username]/japan_rice_2020");
```

Where the image contains values 1=rice, 0=other.

**Option B: Use Existing MODIS Crop Classification**

```javascript
// MODIS Global Crop Classification (MOD12Q1)
var lulc = ee.ImageCollection("MODIS/061/MCD12Q1")
  .filterDate(CONFIG.year + "-01-01", CONFIG.year + "-12-31")
  .first()
  .select("LC_Type1");

// Class 10 = Croplands (includes rice)
var rice_map = lulc.eq(10);
```

**Option C: Use ESA WorldCover**

```javascript
var worldcover = ee.ImageCollection("ESA/WorldCover/v100")
  .filterDate(CONFIG.year + "-01-01", CONFIG.year + "-12-31")
  .first();

// Class 40 = Croplands
var rice_map = worldcover.eq(40);
```

### 4. Run the Script

1. Click **Run** in the top-right corner
2. Monitor progress in the Tasks panel
3. Once data is ready, the script will start exporting results (see Tasks tab)

### 5. Download Results

1. Click **Tasks** tab in the GEE Editor (upper right)
2. For each export task:
   - Click **Run** to start export
   - Check **Google Drive** folder specified in config (default: "AWD")
   - Download .tif files

Expected output files:
- `Japan_AWD_Suitability_All_Thresholds.tif` (multi-band image)

## Output Specification

### File Format

- **Format**: GeoTIFF (Cloud-optimized)
- **Bands**: 7 bands (one per threshold)
  - Band 1: `suitability_-25` (most lenient threshold)
  - Band 2: `suitability_-50`
  - ...
  - Band 7: `suitability_-150` (most stringent threshold)
- **Values**: 1-3 (suitability class)
  - 1 = Low suitability (<33% suitable dekads)
  - 2 = Moderate suitability (33-66% suitable dekads)
  - 3 = High suitability (>66% suitable dekads)
- **Projection**: EPSG:4326 (WGS84)
- **Resolution**: 500 m (as configured)

### Interpretation

For each pixel, values across bands show how suitability classification changes with deficit threshold stringency:

```
Threshold:       -25mm  -50mm  -70mm  -90mm  -110mm -130mm -150mm
Example Pixel:    3      3      2      2      1      1      1
```

This pixel has high suitability under lenient thresholds but drops to low suitability as threshold becomes more stringent. Use as basis for robustness assessment.

## Data Sources

### 1. Rainfall: CHIRPS

- **Collection**: `UCSB-CHG/CHIRPS/DAILY`
- **Resolution**: 5 km
- **Temporal Coverage**: 1981-present (daily)
- **Processing in Script**:
  - Filter to study area and season dates
  - Sum 10-day windows to dekad totals
  - Output units: mm/dekad

```javascript
// Example access:
var chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
  .filterDate("2022-05-01", "2022-09-30")
  .filterBounds(study_area_boundary);
```

### 2. Evapotranspiration: MODIS MOD16A2

- **Collection**: `MODIS/061/MOD16A2`
- **Resolution**: 500 m
- **Temporal Coverage**: 2000-present (8-day)
- **Processing in Script**:
  - Reproject to 500m study grid
  - Convert from 0.1 mm/8-day scale to mm/dekad
  - Weighted overlap interpolation when dekad boundary crosses 8-day tile boundary
  - Output units: mm/dekad

```javascript
// Example access:
var modis_et = ee.ImageCollection("MODIS/061/MOD16A2")
  .filterDate("2022-05-01", "2022-09-30");
```

### 3. Soil Properties: SoilGrids

- **Collections**: 
  - `projects/soilgrids-isric/clay_mean` (clay percentage 0-5cm)
  - `projects/soilgrids-isric/sand_mean` (sand percentage 0-5cm)
- **Resolution**: 250 m
- **Processing in Script**:
  - Calculate clay + sand percentages
  - Classify into 4 texture classes
  - Map texture class to percolation rate (3-12 mm/day)
  - Convert to dekad totals
  - Output units: mm/dekad

```javascript
// Example access:
var clay = ee.Image("projects/soilgrids-isric/clay_mean").divide(10);  // 0-100%
```

### 4. Elevation: SRTM

- **Collection**: `USGS/SRTMGL1_Ellip`
- **Resolution**: 30 m
- **Processing in Script**:
  - Used to compute slope for biophysical constraints
  - Slope threshold: <10° for feasibility
  - Output units: degrees

```javascript
// Example access:
var dem = ee.Image("USGS/SRTMGL1_Ellip");
var slope = ee.Terrain.slope(dem);
```

### 5. Rice Extent Map

- **User-provided or derived** from MODIS/ESA classification
- **Expected values**: 1 (rice) or 0 (other)
- **Resolution**: Any (will be resampled to 500m)

## Advanced Configuration

### Changing Deficit Thresholds

Edit the `deficit_thresholds` array in CONFIG to test different water stress levels:

```javascript
deficit_thresholds: [-10, -30, -50, -80, -120, -200],  // Custom thresholds
```

Lower (more negative) values = stricter criterion = fewer suitable dekads.

### Analyzing Different Years

Change the `year` parameter:

```javascript
year: 2020,  // Or 2019, 2021, etc.
```

The script will automatically adjust all date filters.

### Adjusting Spatial Resolution

Change `output_scale` for coarser/finer output:

```javascript
output_scale: 1000,  // 1 km resolution (faster)
// or
output_scale: 250,   // 250 m resolution (slower, more detail)
```

Higher resolution increases computation time exponentially.

### Using Different Rice Classification

Replace the `rice_map` definition to use alternative data sources:

```javascript
// Option 1: ESA WorldCover 2021 (global, high quality)
var worldcover = ee.ImageCollection("ESA/WorldCover/v200")
  .filterDate("2021-01-01", "2021-12-31")
  .first()
  .select("Map");
var rice_map = worldcover.eq(40);  // Class 40 = Croplands

// Option 2: MODIS LC (annual, consistent time series)
var modis_lc = ee.ImageCollection("MODIS/061/MCD12Q1")
  .filterDate(CONFIG.year + "-01-01", CONFIG.year + "-12-31")
  .first()
  .select("LC_Type1");
var rice_map = modis_lc.eq(10);  // Class 10 = Croplands

// Option 3: Custom asset (best for regional studies)
var rice_map = ee.Image("users/your-username/japan_rice_paddy_map_2020");
```

## Troubleshooting

### Issue: "Image is null" or "No valid data"

**Causes**:
- Study area boundary doesn't overlap with rice extent
- Year has no data for selected collections
- Bounding box coordinates are inverted

**Solutions**:
1. Verify bounding box: `[min_lon, min_lat, max_lon, max_lat]`
2. Check that min_lon < max_lon and min_lat < max_lat
3. Try expanding the study area boundary
4. Verify year is within CHIRPS coverage (1981-present)

### Issue: "Export failed" or "Computation timed out"

**Causes**:
- Study area too large (>1e13 pixels at 500m = ~2.5 million km²)
- Output resolution too fine (250m with large area)
- Too many thresholds being processed

**Solutions**:
1. Reduce study area or increase `output_scale` (coarsen resolution)
2. Reduce number of thresholds in `deficit_thresholds`
3. Split analysis into smaller regions
4. Use export.image.toDrive with default pyramid policy

### Issue: "Authentication failed" or "Access denied"

**Causes**:
- Not logged into Google Earth Engine
- Missing access to shared datasets

**Solutions**:
1. Click "Authorize" when prompted by GEE
2. Ensure you have a Google Earth Engine account (request access at https://earthengine.google.com/signup/)
3. If using user assets, verify ownership

## Performance Optimization

### Reduce Computation Time

```javascript
// Option 1: Reduce spatial resolution
output_scale: 1000  // Default 500m, use 1000m for faster preview

// Option 2: Reduce study area
var study_region = ee.Geometry.rectangle([130, 30, 135, 35]);  // Smaller area

// Option 3: Use fewer thresholds
deficit_thresholds: [-50, -100, -150]  // Instead of 7 thresholds
```

### Monitor Progress

Look at the GEE console (bottom-right) to see:
- Number of tiles being processed
- Current dekad being analyzed
- Estimated remaining time

## Integration with Python Pipeline

After downloading GeoTIFF from Google Drive:

1. Place in `data/raw/gee_exports/`
2. Run Python pipeline:
   ```bash
   python scripts/run_pipeline.py
   ```
3. Pipeline will automatically load and post-process the GEE outputs

## Support & Documentation

- **GEE Documentation**: https://developers.google.com/earth-engine
- **GEE Datasets**: https://developers.google.com/earth-engine/datasets
- **CHIRPS Data Guide**: https://www.chg.ucsb.edu/data/chirps
- **MODIS PET Guide**: https://lpdaac.usgs.gov/products/mod16a2v061/
- **SoilGrids Info**: https://www.isric.org/explore/soilgrids

## Citation

If you use this GEE script, please cite:

```bibtex
@software{tran_awd_gee_2025,
  title={Google Earth Engine Pipeline for AWD Policy Transportability Assessment},
  author={Tran, My},
  year={2025},
  url={https://github.com/MyTran-GitHub/awd-policy-transportability/tree/main/gee}
}
```

---

**Last Updated**: January 2025

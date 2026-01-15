# Data Sources: Accessing and Processing Satellite Data

## Overview

This guide explains how to access, understand, and process the satellite data used in the AWD transportability analysis. All data is obtained through Google Earth Engine (GEE), a free cloud-based platform for geospatial analysis.

---

## 1. Google Earth Engine Setup

### 1.1 Getting Started

1. **Create Google Account** (if you don't have one): https://accounts.google.com/signup
2. **Sign Up for Google Earth Engine**: https://earthengine.google.com/signup/
   - Request access (usually approved within 24-48 hours)
   - You'll receive confirmation email
3. **Access the Code Editor**: https://code.earthengine.google.com/

### 1.2 First Time in GEE

When you first open the Code Editor, you'll see:
- **Left panel:** Script editor (write JavaScript code)
- **Center:** Map display
- **Right panel:** Inspector, Console, Tasks tabs

**Quick test:**
```javascript
// Paste this and click "Run"
var image = ee.Image("COPERNICUS/S2/20170102T101031_20170102T101056_T32UQD");
Map.addLayer(image, {B4: 0.3, B3: 0.2, B2: 0.1}, 'Sentinel-2');
Map.centerObject(image, 11);
```

---

## 2. CHIRPS: Rainfall Data

### 2.1 Dataset Information

| Property | Value |
|----------|-------|
| **Full Name** | Climate Hazards Group Infrared Precipitation with Station Data |
| **GEE Collection** | `UCSB-CHG/CHIRPS/DAILY` |
| **Resolution** | 5 km (0.05° × 0.05°) |
| **Temporal Coverage** | January 1, 1981 – Present |
| **Temporal Frequency** | Daily |
| **Units** | mm/day |
| **Projection** | WGS84 (EPSG:4326) |

### 2.2 Data Quality & Bias

**Strengths:**
- ✅ Combines satellite + rain gauge observations (hybrid approach)
- ✅ Validated against field networks in Africa, Asia, Latin America
- ✅ Openly available with no subscription
- ✅ Consistent long time series (40+ years)

**Known Issues:**
- ⚠️ ±10-15% error in mountainous regions (interpolation uncertainty)
- ⚠️ Occasional data gaps during sensor transitions (corrected retroactively)
- ⚠️ May underestimate convective storms (short duration, high intensity)

**For AWD:** Error magnitude acceptable because we analyze seasonal trends, not individual storm events.

### 2.3 Accessing CHIRPS in GEE

```javascript
// Load daily rainfall data
var chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
  .filterDate("2022-01-01", "2022-12-31")
  .filterBounds(study_area);  // Replace with your geometry

// Aggregate to dekad (10-day sum)
var dekad_start = ee.Date("2022-05-15");  // May 15 = start of season
var rainfall_dekad = chirps
  .filterDate(dekad_start, dekad_start.advance(10, "day"))
  .sum();

// Print statistics
print("CHIRPS Rainfall Statistics:", rainfall_dekad.reduceRegion({
  reducer: ee.Reducer.minMax(),
  geometry: study_area,
  scale: 5000
}));
```

### 2.4 Known Caveat: Japan & East Asia

CHIRPS has **lower gauge density** in Japan compared to Africa. Recommend:
- Cross-reference with Japan Meteorological Agency (JMA) data for validation
- Use CHIRPS for spatial patterns (relative comparison)
- Consider ±15% uncertainty bounds in suitability estimates

### 2.5 Alternative Sources

| Dataset | Resolution | Frequency | Coverage |
|---------|-----------|-----------|----------|
| **MERRA-2** | 50 km | Daily | Global (1980-present) |
| **IMERG** | 10 km | 30-min | Tropics/subtropics (2000-present) |
| **Japan JMA** | 5 km | Daily | Japan only (1900-present) |

For most applications, CHIRPS is recommended balance of accuracy, resolution, and global coverage.

---

## 3. MODIS PET: Evapotranspiration Data

### 3.1 Dataset Information

| Property | Value |
|----------|-------|
| **Full Name** | Moderate Resolution Imaging Spectroradiometer Evapotranspiration (MOD16A2) |
| **GEE Collection** | `MODIS/061/MOD16A2` |
| **Resolution** | 500 m (0.00417° × 0.00417°) |
| **Temporal Coverage** | January 2000 – Present |
| **Temporal Frequency** | 8-day composite |
| **Units** | mm/8-day (scale factor: 0.1) |
| **Projection** | Sinusoidal (reprojected to WGS84 in GEE) |

### 3.2 Understanding ET Data

**Reference Evapotranspiration (ET0):**
- ET0 = standardized evapotranspiration for short grass
- Rice ET ≈ 0.9-1.1 × ET0 (depends on variety, growth stage)
- MODIS ET includes both canopy transpiration + soil evaporation

**Why MODIS is useful:**
- ✅ Accounts for seasonal vegetation changes (NDVI-based)
- ✅ 500m resolution captures field-scale heterogeneity
- ✅ Consistent global product since 2000
- ✅ Validated against flux towers (±10% error typical)

### 3.3 Accessing MODIS in GEE

```javascript
// Load MODIS ET
var modis_et = ee.ImageCollection("MODIS/061/MOD16A2")
  .filterDate("2022-05-01", "2022-09-30")
  .filterBounds(study_area);

// Prepare for processing
var et_processed = modis_et.map(function(image) {
  return image
    .multiply(0.1)  // Convert from 0.1mm to mm
    .clip(study_area)
    .reproject({
      crs: "EPSG:4326",
      scale: 500
    });
});

// Extract single image for dekad
var et_dekad = et_processed
  .filterDate("2022-05-15", "2022-05-25")
  .mean();

print("MODIS ET Range:", et_dekad.reduceRegion({
  reducer: ee.Reducer.minMax(),
  geometry: study_area,
  scale: 500
}));
```

### 3.4 Dekad Interpolation

Since MODIS is 8-day and our analysis is 10-day (dekad):

**When dekad boundary crosses 8-day tile boundary:**

```
8-day tiles:    [May 1-8] [May 9-16] [May 17-24] ...
Dekads:         [May 1-10] [May 11-20] ...
                     ↓ conflict
```

**Solution: Weighted average**

If dekad May 1-10 overlaps:
- May 1-8 tile: 8 days of weight
- May 9-16 tile: 2 days of weight

$$ET_{dekad} = \frac{8 \times ET_1 + 2 \times ET_2}{10}$$

Code implementation provided in `gee/water_balance_suitability.js`.

### 3.5 Alternative ET Sources

| Dataset | Resolution | Frequency | Validation |
|---------|-----------|-----------|-----------|
| **MODIS MOD16A2** | 500 m | 8-day | Well-validated (flux towers) |
| **FLDAS** | 10 km | Daily | Good for Africa |
| **MERRA-2** | 50 km | 3-hourly | Coarse for field-level |
| **GLEAM** | 25 km | Daily | Global, experimental |

**Recommendation:** MODIS is best for rice because resolution balances accuracy and coverage.

---

## 4. SoilGrids: Soil Properties

### 4.1 Dataset Information

| Property | Value |
|----------|-------|
| **Full Name** | Soil properties predicted at standard depths |
| **GEE Source** | `projects/soilgrids-isric/clay_mean` (and sand_mean) |
| **Resolution** | 250 m |
| **Depth** | 0-5 cm (topsoil) |
| **Content** | Clay (%), Sand (%), Silt (%) |
| **Global Coverage** | Yes |
| **Update Frequency** | Static (2017-2021 snapshot) |

### 4.2 Data Interpretation

**What are these percentages?**
- **Clay (%):** Particles <0.002 mm; high clay = poor drainage
- **Sand (%):** Particles 0.05-2 mm; high sand = good drainage
- **Silt (%):** Particles 0.002-0.05 mm; intermediate properties

**Soil Texture Triangle:**
```
                           Clay
                            /\
                           /  \
                          /    \
                         /      \
                        /        \
                      Clay      Silt
                    Loam    Loam
                   /            \
                  /              \
           Sandy            Silty
           Clay             Clay
             / \            / \
            /   \          /   \
        Sandy    \        /   Silt
        Loam      \      /    Loam
                   \    /
                    \  /
                   Loamy Sand
                    /\
                   /  \
                  /    \
              Sand     Loamy
                      Sand
```

### 4.3 Accessing SoilGrids in GEE

```javascript
// Load soil properties
var clay = ee.Image("projects/soilgrids-isric/clay_mean");
var sand = ee.Image("projects/soilgrids-isric/sand_mean");

// Scale to percentages (SoilGrids stored as deci-percent: 0-1000)
clay = clay.divide(10);  // Convert to 0-100%
sand = sand.divide(10);

// Calculate silt
var silt = clay.expression("100 - c - s", {c: clay, s: sand});

// Classify into drainage classes
var drainage = clay.expression(
  "c < 20 ? 1 : (c < 35 ? 2 : (c < 50 ? 3 : 4))",
  {c: clay}
);

print("Drainage Class Distribution:", drainage.reduceRegion({
  reducer: ee.Reducer.histogram(),
  geometry: study_area,
  scale: 250
}));
```

### 4.4 Limitations of SoilGrids

⚠️ **Coarse spatial interpolation:**
- Based on ~150,000 soil profile samples globally
- Density low in some regions (e.g., SE Asia)
- Spatial interpolation assumes smooth gradients

⚠️ **Snapshot in time:**
- Represents ~2017-2021 conditions
- Soil properties change slowly but do evolve
- Not updated for recent drainage modifications

⚠️ **Limited depth:**
- Only 0-5 cm (topsoil)
- Rice percolation influenced by subsoil layers (not captured)
- Percolation rates are approximate

**Mitigation:** Use SoilGrids for *relative* comparisons, not absolute rates. Cross-validate with field surveys in high-value zones.

### 4.5 Alternative Soil Data

| Source | Coverage | Resolution | Depth |
|--------|----------|-----------|-------|
| **SoilGrids 250m** | Global | 250 m | 6 standard depths |
| **Japan Soil Map** | Japan only | 1:50,000 | Full profile |
| **HWSD v2** | Global | 1 km | Multiple layers |
| **Field surveys** | Local | <100 m | Complete profile |

---

## 5. SRTM: Digital Elevation Model

### 5.1 Dataset Information

| Property | Value |
|----------|-------|
| **Full Name** | Shuttle Radar Topography Mission DEM |
| **GEE Collection** | `USGS/SRTMGL1_Ellip` |
| **Resolution** | 30 m |
| **Vertical Accuracy** | ±10 m (RMSE) |
| **Coverage** | ±60° latitude |
| **Projection** | WGS84 ellipsoid |

### 5.2 Using SRTM for Slope

```javascript
// Load DEM
var dem = ee.Image("USGS/SRTMGL1_Ellip").select("elevation");

// Compute slope (degrees)
var slope = ee.Terrain.slope(dem);

// Classify feasibility
var slope_feasible = slope.lte(10);  // < 10 degrees

print("Feasible Area:", slope_feasible.reduceRegion({
  reducer: ee.Reducer.mean(),
  geometry: study_area,
  scale: 30
}));
```

### 5.3 Slope Interpretation for Rice

**Why slope matters for AWD:**
- Flat terrain (< 5°): Easy to manage water levels uniformly
- Moderate slope (5-10°): Possible with terracing or careful design
- Steep slope (> 10°): Impractical for flood-and-drain cycles
- Very steep (> 25°): Unsuitable for paddy rice entirely

**Japan specific:** Much of Japan is mountainous, so slope is major constraint.

---

## 6. Rice Extent Map

### 6.1 Obtaining Rice Data

**Three options:**

**Option 1: Use MODIS Land Use Classification** (Recommended if no better data)
```javascript
var modis_lulc = ee.ImageCollection("MODIS/061/MCD12Q1")
  .filterDate("2022-01-01", "2022-12-31")
  .first()
  .select("LC_Type1");

// Class 10 = Croplands (includes rice and other crops)
var rice_mask = modis_lulc.eq(10);
```

**Option 2: Use ESA WorldCover** (Higher resolution, global)
```javascript
var worldcover = ee.ImageCollection("ESA/WorldCover/v200")
  .filterDate("2021-01-01", "2021-12-31")
  .first();

// Class 40 = Croplands
var rice_mask = worldcover.eq(40);
```

**Option 3: Use Custom Asset** (Best if you have field data)
```javascript
// Upload your own classified map
var rice_map = ee.Image("users/your-username/japan_rice_2020");
```

### 6.2 Classification Accuracy

| Source | Overall Accuracy | Rice-specific | Notes |
|--------|-----------------|----------------|-------|
| **MODIS** | 70-80% | 60-70% | Coarse (500m), misses small plots |
| **ESA WorldCover** | 75-85% | 70-75% | Better resolution (10m) |
| **Custom field survey** | 95%+ | 95%+ | Most accurate but labor-intensive |

For Japan, ESA WorldCover is recommended due to precise boundaries.

---

## 7. Data Workflow in the Pipeline

### 7.1 Step-by-Step Data Flow

```
1. Google Earth Engine Script (gee/water_balance_suitability.js)
   ├─ Load CHIRPS daily rainfall
   ├─ Aggregate to dekads (10-day sums)
   ├─ Load MODIS ET, interpolate to dekads
   ├─ Load SoilGrids clay/sand, compute percolation
   ├─ Compute water balance: WB = P - ET - K
   ├─ Test across 7 deficit thresholds
   ├─ Classify suitability (1=Low, 2=Moderate, 3=High)
   └─ Export multi-band GeoTIFF to Google Drive

2. Download from Google Drive
   └─ Save to data/raw/gee_exports/

3. Python Pipeline (scripts/run_pipeline.py)
   ├─ Load GeoTIFF from data/raw/
   ├─ Validate data quality
   ├─ Analyze fragmentation
   ├─ Compute regional statistics
   └─ Generate visualizations
   
4. Outputs
   ├─ outputs/figures/*.png (publication-ready)
   └─ outputs/tables/*.csv (statistical summaries)
```

### 7.2 Computational Efficiency

GEE handles large data:
- CHIRPS: 40+ years × 365 days = 15,000 images
- MODIS: 23 years × 46 composites = 1,000 images
- Each analysis at 500m resolution over Japan

**Cloud processing eliminates:** Data downloading, local storage, processing time

**You only receive:** Final analysis-ready GeoTIFF (~50 MB)

---

## 8. Accessing Data Outside of AWD Pipeline

### 8.1 Manual GEE Queries

If you want to explore data independently:

```javascript
// Open https://code.earthengine.google.com/

// Example 1: Visualize 2022 rainfall pattern
var chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
  .filterDate("2022-05-01", "2022-09-30")
  .sum();

Map.addLayer(chirps, {min: 0, max: 1000}, "Total Rainfall May-Sep 2022");
Map.centerObject(chirps.geometry(), 6);

// Example 2: Compare rice area over time
var rice_2020 = ee.ImageCollection("MODIS/061/MCD12Q1")
  .filterDate("2020-01-01", "2020-12-31")
  .first()
  .select("LC_Type1")
  .eq(10);

var rice_2022 = ee.ImageCollection("MODIS/061/MCD12Q1")
  .filterDate("2022-01-01", "2022-12-31")
  .first()
  .select("LC_Type1")
  .eq(10);

print("Rice area 2020:", rice_2020.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: study_area,
  scale: 500
}));
```

### 8.2 Exporting Data Manually

```javascript
// Export rainfall to GeoTIFF
Export.image.toDrive({
  image: chirps,
  description: "CHIRPS_May_Sep_2022",
  folder: "GEE_Exports",
  scale: 5000,
  crs: "EPSG:4326",
  region: study_area.bounds()
});
```

---

## 9. Data Quality Checklist

Before using GEE exports:

- ☐ Verify bounding box matches study area
- ☐ Check no-data pixels (should be <5% for study area)
- ☐ Examine histograms (no outliers or gaps)
- ☐ Cross-reference with ground truth (if available)
- ☐ Document data year and processing date
- ☐ Version control GEE script (archive copies)

---

## 10. Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| "Image is null" | Study area outside dataset bounds | Verify coordinates, expand bounding box |
| No data pixels | Wrong date range | Check dataset temporal coverage |
| Slow processing | Too many images / high resolution | Reduce study area or increase scale |
| Export failed | Computation timed out | Reduce resolution, split into regions |
| Different results than paper | Different year/season | Ensure same temporal window |

---

## References

- **CHIRPS:** Funk et al. (2015) Scientific Data
- **MODIS ET:** Running et al. (2017) BioScience
- **SoilGrids:** Hengl et al. (2017) PLoS ONE
- **SRTM:** Farr et al. (2007) Reviews of Geophysics
- **GEE:** Gorelick et al. (2017) Remote Sensing of Environment

---

**Document Version:** 1.0  
**Last Updated:** January 2026  
**Related Files:** `gee/water_balance_suitability.js`, `src/data_acquisition/__init__.py`

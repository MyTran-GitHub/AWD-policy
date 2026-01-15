# Reproduction Guide: Running the Full Analysis

## Quick Summary

**Time required:** 4-6 hours total (mostly waiting for GEE processing)
- 30 min: Setup & configuration
- 2-3 hours: Google Earth Engine processing
- 30 min: Data download
- 1-2 hours: Python pipeline execution
- 30 min: Visualization & inspection

**Cost:** Free (all tools are open-source)

---

## Part 1: Environment Setup (30 minutes)

### 1.1 Install Anaconda (if needed)

If you don't have Python installed:

```bash
# Download from: https://www.anaconda.com/download
# Follow installation wizard (default settings OK)

# Verify installation
conda --version
```

### 1.2 Clone Repository

```bash
# Navigate to desired location
cd ~/Documents  # Or your preferred location

# Clone the repo
git clone https://github.com/MyTran-GitHub/AWD-policy.git
cd AWD-policy
```

### 1.3 Create Conda Environment

```bash
# Create isolated Python environment with correct packages
conda create -n awd python=3.9

# Activate environment
conda activate awd

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import numpy, pandas, rasterio, geopandas; print('✅ All packages installed')"
```

### 1.4 Check Configuration

```bash
# Review default parameters
cat config/config.yaml | head -50

# You should see:
#   study_areas:
#     japan: {...}
#     vietnam: {...}
#   water_balance:
#     season: {...}
#     deficit_thresholds: [-25, -50, -70, ...]
```

---

## Part 2: Google Earth Engine Data Processing (2-3 hours)

### 2.1 Create Google Earth Engine Account

1. Go to https://earthengine.google.com/signup/
2. Sign in with your Google account
3. Accept terms and submit request
4. **Wait for approval email** (usually 24-48 hours)

### 2.2 Access the Code Editor

Once approved:

1. Go to https://code.earthengine.google.com/
2. You should see the JavaScript editor
3. Bookmark this page (you'll use it often)

### 2.3 Prepare Your Study Area (Optional)

If analyzing beyond Japan:

```javascript
// In GEE Code Editor, define your study area geometry:

var study_area = ee.Geometry.Rectangle([
  130.5,  // min_lon
  30.5,   // min_lat
  145.5,  // max_lon
  45.5    // max_lat
]);

// Or use an existing administrative boundary:
var japan = ee.FeatureCollection("FAO/GAUL/2015/level0")
  .filter(ee.Filter.eq("ADM0_NAME", "Japan"));
```

### 2.4 Run the GEE Pipeline

**Method 1: Copy-Paste (Recommended for first time)**

```javascript
// 1. Open the GEE Code Editor: https://code.earthengine.google.com/
// 2. Create a new script (click "New" → "Script")
// 3. Copy entire contents from: gee/water_balance_suitability.js
// 4. Paste into the GEE editor
// 5. Review configuration block at top:
//    - year: 2022
//    - season dekads: 10-28
//    - deficit thresholds: [-25, -50, -70, -90, -110, -130, -150]
// 6. Click the "Run" button (top-right)
// 7. Monitor console output for errors
```

**Configuration Review (first 20 lines of script):**

```javascript
// CONFIGURATION BLOCK - Customize here before running
var CONFIG = {
  year: 2022,                                    // Analysis year
  season: {dekad_start: 10, dekad_end: 28},     // Season (dekad 10=May1, 28=Sep25)
  exclusion_windows: {exclude_first: 2, exclude_last: 1},  // Skip establishment/harvest
  deficit_thresholds: [-25, -50, -70, -90, -110, -130, -150],  // Sensitivity thresholds
  irrigation_threshold: 5.0,                     // Minimum rainfall (mm) to avoid irrigation
  output_scale: 500,                             // Output resolution (meters)
  max_pixels: 1e13,                              // Max computation pixels
  study_region: ee.Geometry.Rectangle([130.5, 30.5, 145.5, 45.5])  // Japan bounds
};

// STUDY AREA - Load rice extent
var rice_map = ee.Image("users/your-username/japan_rice_2020");  // Edit this!
// OR use MODIS:
var lulc = ee.ImageCollection("MODIS/061/MCD12Q1")
  .filterDate("2022-01-01", "2022-12-31").first();
var rice_map = lulc.eq(10);
```

**Edit the rice_map line** to match your data:

```javascript
// Option A: If you uploaded your own rice map
var rice_map = ee.Image("users/YOUR-USERNAME/japan_rice_2020");

// Option B: Use MODIS global croplands
var rice_map = ee.ImageCollection("MODIS/061/MCD12Q1")
  .filterDate("2022-01-01", "2022-12-31")
  .first()
  .select("LC_Type1")
  .eq(10);  // Class 10 = Croplands

// Option C: Use ESA WorldCover (recommended for Japan)
var rice_map = ee.ImageCollection("ESA/WorldCover/v200")
  .filterDate("2021-01-01", "2021-12-31")
  .first()
  .eq(40);  // Class 40 = Croplands
```

### 2.5 Monitor Processing

After clicking "Run":

1. **Check Console:** Look for any error messages (red text)
2. **Monitor Progress:** GEE shows estimated remaining time
3. **Expected duration:** 5-15 minutes depending on study area size
4. **Success indicator:** No error messages in console

### 2.6 Check Export Tasks

```
1. Click the "Tasks" tab (top-right of editor)
2. You should see export task(s) listed:
   - Status initially "READY"
   - Click "RUN" to start export to Google Drive
3. Monitor status:
   - RUNNING: Processing
   - COMPLETED: Ready to download
   - FAILED: Check error message
```

**Expected output:**
- File: `Japan_AWD_Suitability_All_Thresholds.tif`
- Size: 50-200 MB (depends on area)
- Format: GeoTIFF with 7 bands (one per threshold)
- Location: Google Drive → AWD folder

### 2.7 Download Data

```
1. Open Google Drive: https://drive.google.com/
2. Navigate to folder "AWD"
3. Right-click on GeoTIFF file
4. Select "Download"
5. Save to: awd-policy-transportability/data/raw/gee_exports/
```

**Verify download:**
```bash
# In terminal
ls -lh data/raw/gee_exports/
# Should show: Japan_AWD_Suitability_All_Thresholds.tif (~100 MB)
```

---

## Part 3: Python Pipeline Execution (1-2 hours)

### 3.1 Activate Environment

```bash
# Navigate to repo directory
cd awd-policy-transportability

# Activate environment
conda activate awd

# Verify you're in right place
pwd  # Should end in: awd-policy-transportability
```

### 3.2 Run Full Pipeline

```bash
# Execute full analysis pipeline
python scripts/run_pipeline.py

# Expected output:
#   2026-01-15 10:23:45 - INFO - Loading configuration...
#   2026-01-15 10:23:46 - INFO - Validating inputs...
#   2026-01-15 10:23:47 - INFO - Processing water balance...
#   [... progress messages ...]
#   2026-01-15 10:45:12 - INFO - ✅ Pipeline completed successfully!
```

### 3.3 Run Single Study Area (Optional)

```bash
# Analyze only Japan (faster)
python scripts/run_pipeline.py --study-area japan

# Or only Vietnam
python scripts/run_pipeline.py --study-area vietnam

# Skip visualization (if display issues)
python scripts/run_pipeline.py --skip-viz
```

### 3.4 Monitor Execution

The pipeline has 5 stages with logging:

| Stage | Time | Output |
|-------|------|--------|
| 1. Data Loading | 30 sec | Confirms GEE export loaded successfully |
| 2. Validation | 30 sec | Data shape, value ranges, no-data pixels |
| 3. Water Balance | 10 sec | Suitability statistics |
| 4. Spatial Analysis | 30 sec | Fragmentation metrics, regional stats |
| 5. Visualization | 2 min | Generates PNG figures |

---

## Part 4: Inspect Results (30 minutes)

### 4.1 Check Output Structure

```bash
# View all generated files
ls -R outputs/

# You should see:
# outputs/
# ├── japan/
# │   ├── threshold_sensitivity.csv
# │   ├── regional_statistics.txt
# │   ├── fragmentation_metrics.json
# │   └── ...
# └── figures/
#     ├── japan_suitability_map.png
#     ├── vietnam_japan_comparison.png
#     ├── threshold_sensitivity.png
#     └── fragmentation_comparison.png
```

### 4.2 Review Key Statistics

```bash
# View threshold sensitivity analysis
cat outputs/japan/threshold_sensitivity.csv

# Expected output:
# threshold_mm,fraction_suitable,suitability_class,percentage_suitable
# -25,0.75,3,75.0
# -50,0.60,2,60.0
# ...
```

Interpretation:
- **-25 mm threshold:** 75% of season suitable for AWD (High)
- **-150 mm threshold:** 5% of season suitable (Low)
- **Takeaway:** Suitability decreases with stricter thresholds

### 4.3 Examine Regional Breakdown

```bash
# View regional statistics
cat outputs/japan/regional_statistics.txt

# Expected format:
# Region: Kanto
#   Suitable pixels: 45,000
#   Suitability: 65%
# Region: Tohoku
#   Suitable pixels: 28,000
#   Suitability: 42%
# ...
```

### 4.4 View Generated Maps

```bash
# List all figures
ls outputs/figures/

# Open in image viewer:
open outputs/figures/japan_suitability_map.png  # macOS
# or
xdg-open outputs/figures/japan_suitability_map.png  # Linux
# or
start outputs/figures/japan_suitability_map.png  # Windows
```

**Map interpretation:**
- **Green areas:** High suitability (suitable for AWD)
- **Yellow areas:** Moderate suitability
- **Red areas:** Low suitability (not suitable for AWD)
- **Gray areas:** No data (non-rice area)

---

## Part 5: Validation Against Portfolio

### 5.1 Check Key Results

Verify your outputs match [project-transfer.html](../project-transfer.html):

```bash
# Extract Japan suitability from CSV
grep "^3" outputs/japan/threshold_sensitivity.csv | head -1

# Should show ~0.15-0.20 fraction suitable at threshold -50
# This translates to 15-20% high suitability (close to portfolio's 18%)
```

### 5.2 Fragmentation Comparison

```bash
# Check fragmentation index
cat outputs/japan/fragmentation_metrics.json | grep -A 2 "fragmentation_index"

# Should show Japan ~0.25 vs Vietnam ~0.1
# Ratio ≈ 2.5× (portfolio reports 3.8×, difference may be due to:
#   - Different year/season
#   - Different rice extent map
#   - Biophysical constraints weighting)
```

### 5.3 Regional Distribution

```bash
# Check if Kanto has highest suitability (as reported in portfolio)
grep "Kanto" outputs/japan/regional_statistics.txt

# Should show ~60-70% suitability (matches portfolio's "High")
```

---

## Troubleshooting

### Issue: GEE Script Error

**Symptom:** Red error message in GEE console

**Solutions:**
```javascript
// Check 1: Verify rice_map is defined
print("Rice map extent:", rice_map.geometry().bounds());

// Check 2: Verify study region is valid
print("Study region:", CONFIG.study_region);

// Check 3: Check data availability for year
var chirps_check = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
  .filterDate(CONFIG.year + "-01-01", CONFIG.year + "-12-31");
print("CHIRPS images available:", chirps_check.size());
```

### Issue: "No valid data" after loading GEE export

```bash
# Check file exists and is readable
file data/raw/gee_exports/Japan_AWD_Suitability_All_Thresholds.tif

# Check file size (should be >50MB)
du -h data/raw/gee_exports/

# Check with GDAL (if installed)
gdalinfo data/raw/gee_exports/Japan_AWD_Suitability_All_Thresholds.tif | head -20
```

### Issue: Python script crashes

```bash
# Run with verbose logging
python scripts/run_pipeline.py -v DEBUG

# Or check logs directory
tail -100 logs/pipeline.log
```

### Issue: Different results than expected

**Common causes:**
- Different year (use consistent year across all analyses)
- Different rice extent map (MODIS vs ESA vs custom)
- Different GEE parameters (check config block)
- Data updates (satellite data updated regularly)

**Solution:** Re-run GEE with exact same parameters documented in your config.

---

## Advanced: Customization

### Analyze Different Year

```bash
# In GEE script, change:
var CONFIG = {
  year: 2021,  // <- Change this
  ...
};

# Re-run script and download new export
```

### Analyze Different Region

```bash
# In GEE script, change study_region:
var CONFIG = {
  year: 2022,
  study_region: ee.Geometry.Rectangle([
    100.5,  // min_lon (Vietnam)
    8.5,    // min_lat
    107.5,  // max_lon
    22.5    // max_lat
  ]),
  ...
};
```

### Adjust Deficit Thresholds

```bash
# In config/config.yaml:
water_balance:
  deficit_thresholds: [-25, -50, -75, -100, -150]  # <- Customize
```

Then re-run Python pipeline.

---

## Next Steps After Successful Run

1. **Document your parameters:**
   ```bash
   # Save configuration snapshot
   cp config/config.yaml config/config_2026-01-15_japan.yaml
   ```

2. **Compare with portfolio:**
   - Does Japan suitability ≈ 18%?
   - Does fragmentation show 3.8× pattern?
   - Do regional patterns match (Kanto highest)?

3. **Generate publication figures:**
   ```bash
   # Copy outputs to presentation
   cp outputs/figures/*.png ~/Documents/MyPresentation/
   ```

4. **Push results to GitHub:**
   ```bash
   # Add outputs (optional) to track results
   git add outputs/
   git commit -m "Results from 2022 analysis: Japan 18% suitability, 3.8× fragmentation"
   ```

---

## Useful Commands Reference

```bash
# Activate environment
conda activate awd

# Run full pipeline
python scripts/run_pipeline.py

# Run single study area
python scripts/run_pipeline.py --study-area japan

# View logs
tail -50 logs/pipeline.log

# Check output files
ls -lh outputs/japan/
ls -lh outputs/figures/

# Clean outputs (start fresh)
rm -rf outputs/ logs/

# Deactivate environment
conda deactivate
```

---

## Duration Summary

| Task | Time |
|------|------|
| Environment setup | 30 min |
| GEE account setup | 24 hours (waiting) |
| GEE script execution | 10 min |
| Data download | 10 min |
| Python pipeline | 20 min |
| Result inspection | 20 min |
| **Total (active)** | **~1.5 hours** |
| **Total (with waiting)** | **~24 hours** |

---

## Questions?

- **GEE issues?** See `docs/data_sources.md` and `gee/README.md`
- **Methodology?** See `docs/methodology.md`
- **Code issues?** Check `README.md` and inline code comments
- **Comparison with portfolio?** See `project-transfer.html` in portfolio directory

---

**Guide Version:** 1.0  
**Last Updated:** January 2026  
**Related Files:** `README.md`, `gee/README.md`, `scripts/run_pipeline.py`

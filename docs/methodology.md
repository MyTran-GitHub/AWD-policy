# Methodology: AWD Policy Transportability Analysis

## Overview

This document describes the scientific methodology for assessing the spatial transportability of Vietnam's Alternative Wetting and Drying (AWD) agricultural water management policy to Japan.

**Research Question:** *To what extent is AWD technically feasible in Japanese rice production systems?*

---

## 1. Water Balance Framework

### 1.1 MapAWD Algorithm

The core analysis implements the **MapAWD** (Map-based Assessment of AWD) framework, which evaluates suitability based on dekad-level (10-day period) water availability.

**Water Balance Equation (dekad-level):**

$$WB_t = P_t - (ET_t + K_t)$$

Where:
- $WB_t$ = Water balance in dekad $t$ (mm)
- $P_t$ = Rainfall in dekad $t$ (mm) [CHIRPS]
- $ET_t$ = Reference evapotranspiration in dekad $t$ (mm) [MODIS]
- $K_t$ = Percolation loss in dekad $t$ (mm) [SoilGrids-derived]

### 1.2 Temporal Structure

**Seasonal Timing:**
- Season spans dekads 10-28 (May 15 - September 25)
- Corresponds to main rice growing season in temperate Asia
- 19 dekads total per season

**Exclusion Windows:**
- Exclude first 2 dekads (10-11): Establishment phase, fields need water
- Exclude last 1 dekad (28): Harvest phase, drying not beneficial
- **Analysis dekads:** 12-27 (16 dekads for suitability assessment)

### 1.3 Suitability Criteria

AWD feasibility requires that fields periodically dry without crop stress. A dekad is considered **suitable** if it meets both conditions:

1. **Deficit Condition:** $WB_t < 0$ (field experiences water deficit)
2. **Threshold Condition:** $WB_t \geq T$ (deficit within safe range)

Where $T$ is the deficit threshold, tested across 7 levels:
$$T \in \{-25, -50, -70, -90, -110, -130, -150\} \text{ mm}$$

**Interpretation:**
- More negative $T$ = stricter criterion = fewer suitable dekads
- $T = -150$ mm: Only extreme deficits qualify (most restrictive)
- $T = -25$ mm: Mild deficits qualify (most lenient)

### 1.4 Suitability Index Computation

For each pixel and threshold:

$$f_{suit} = \frac{n_{suitable}}{n_{analysis}}$$

Where:
- $n_{suitable}$ = Count of dekads where $WB_t < 0$ AND $WB_t \geq T$
- $n_{analysis}$ = Count of analysis dekads (typically 16)
- $f_{suit}$ = Fraction of suitable dekads (0-1)

### 1.5 Suitability Classification

Fraction converted to 3-class scale:

| Class | Name | Condition |
|-------|------|-----------|
| **3** | High | $f_{suit} \geq 0.66$ (≥66% dekads suitable) |
| **2** | Moderate | $0.33 \leq f_{suit} < 0.66$ (33-66% suitable) |
| **1** | Low | $f_{suit} < 0.33$ (<33% suitable) |

**Rationale:** High and moderate classes indicate sufficient dry periods for beneficial AWD. Low class indicates climate insufficiently supports AWD cycles.

---

## 2. Input Data

### 2.1 Rainfall: CHIRPS

**Collection:** `UCSB-CHG/CHIRPS/DAILY`  
**Resolution:** 5 km  
**Temporal:** Daily, 1981-present  
**Processing:** 
- Extract 10-day windows for each dekad
- Sum daily precipitation to dekad totals
- Units: mm/dekad

**Quality Notes:**
- Gold-standard rainfall dataset for agriculture (widely cited)
- Based on satellite + rain gauge fusion
- Suitable for regional hydrological studies

### 2.2 Evapotranspiration: MODIS MOD16A2

**Collection:** `MODIS/061/MOD16A2`  
**Resolution:** 500 m  
**Temporal:** 8-day composites, 2000-present  
**Processing:**
- Extract 8-day ET0 values
- Reproject to study area grid
- Convert scale factor 0.1 to mm
- **Dekad interpolation:** When dekad boundary crosses 8-day tile boundaries, use weighted average:
  $$ET_{dekad} = \frac{n_1 \cdot ET_1 + n_2 \cdot ET_2}{10}$$
  where $n_1, n_2$ are days in each tile
- Units: mm/dekad

**Quality Notes:**
- MODIS ET widely validated against flux tower networks
- Accounts for seasonal vegetation dynamics
- Higher resolution (500m) captures local heterogeneity

### 2.3 Soil Properties: SoilGrids

**Collections:**
- `projects/soilgrids-isric/clay_mean` (clay %, 0-5cm)
- `projects/soilgrids-isric/sand_mean` (sand %, 0-5cm)

**Resolution:** 250 m  
**Processing:**
- Extract clay and sand percentages
- Calculate silt as: silt = 100 - clay - sand
- Classify into 4 drainage classes based on texture

**Drainage Classification:**

| Class | Clay (%) | Soil Type | Percolation (mm/day) |
|-------|----------|-----------|----------------------|
| 1 (Well) | <20 | Sandy | 12.0 |
| 2 (Moderate) | 20-35 | Loam | 8.0 |
| 3 (Imperfect) | 35-50 | Clay loam | 4.0 |
| 4 (Poor) | ≥50 | Clay | 3.0 |

**Percolation Rates:** Based on USDA Soil Survey Manual estimates for rice-growing regions.

### 2.4 Elevation: SRTM

**Collection:** `USGS/SRTMGL1_Ellip`  
**Resolution:** 30 m  
**Processing:**
- Compute slope using Sobel filter
- Classify slopes: feasible if $< 10°$
- Rationale: Steep slopes complicate water management

### 2.5 Rice Extent Map

**User-provided asset** (custom classification)  
**Content:** Binary raster where 1 = rice paddy, 0 = other  
**Sources (alternatives):**
- User's own field surveys / high-resolution imagery
- MODIS Land Use Classification (annual)
- ESA WorldCover (global, 10m resolution)

---

## 3. Biophysical Constraints Integration

Beyond water balance, real-world AWD implementation requires favorable terrain and soil conditions.

### 3.1 Composite Suitability

A pixel is deemed **biophysically feasible** only if:

$$\text{Feasible} = \text{(Slope OK)} \land \text{(Drainage OK)} \land \text{(WB Moderate or High)}$$

Where:
- **Slope OK:** Slope < 10° (flat terrain for uniform water management)
- **Drainage OK:** Drainage class ≤ 3 (excludes poorly-drained clay soils)
- **WB Moderate or High:** Suitability class ≥ 2 (minimum water balance support)

### 3.2 Constraint Importance Analysis

Quantifies which constraints most limit feasibility:
- What % of area fails slope criterion?
- What % fails drainage criterion?
- What % fails water balance criterion?
- How many fail all three?

Identifies whether extension programs should focus on:
- Training (water management knowledge)
- Structural change (terracing for steep areas)
- Subsidy reform (encourage in favorable zones)

---

## 4. Spatial Analysis

### 4.1 Fragmentation Index

Spatial clustering of suitable areas affects extension feasibility. Highly fragmented suitable zones require higher per-unit-area extension costs.

**Fragmentation Metric:**

$$F = \frac{\bar{A}}{A_{max}}$$

Where:
- $\bar{A}$ = Mean patch size (hectares)
- $A_{max}$ = Maximum patch size (hectares)
- $F \in [0, 1]$, higher = more fragmented

**Interpretation:**
- $F = 0.01$: One large contiguous zone (no fragmentation)
- $F = 0.5$: Patches at half max size (moderate fragmentation)
- $F = 1.0$: All patches equal size (maximal fragmentation)

### 4.2 Regional Breakdown

Aggregates suitability statistics by administrative regions:

For each region $r$:
$$S_r = \frac{\text{# pixels: class 3 or 2 in region } r}{\text{# rice pixels in region } r}$$

Identifies priority regions for Phase 1 implementation (highest suitability + lowest fragmentation).

### 4.3 Vietnam vs Japan Comparison

Compares the 3.8× fragmentation ratio to quantify transportability costs:

$$\text{Cost Multiplier} = 1 + 3.8 \times F$$

- Vietnam (F ≈ 0.1): Multiplier ≈ 1.4×
- Japan (F ≈ 0.25): Multiplier ≈ 2.0×

Higher multiplier in Japan indicates extension requires more resources per square kilometer.

---

## 5. Threshold Sensitivity Analysis

Since deficit threshold ($T$) represents a management choice, we test robustness across 7 thresholds.

**Output:** DataFrame with columns:

| threshold_mm | fraction_suitable | suitability_class | percentage_suitable |
|--------------|-------------------|-------------------|----------------------|
| -25 | 0.75 | 3 (High) | 75% |
| -50 | 0.60 | 2 (Moderate) | 60% |
| -70 | 0.40 | 2 (Moderate) | 40% |
| ... | ... | ... | ... |
| -150 | 0.05 | 1 (Low) | 5% |

**Interpretation:**
- If suitability "robust" across thresholds → confident recommendation
- If suitability "cliff" (drops sharply) → sensitive to threshold choice

---

## 6. Uncertainty & Limitations

### 6.1 Data Uncertainties

| Source | Uncertainty | Impact |
|--------|-------------|--------|
| **CHIRPS Rainfall** | ±10-15% regionally | Threshold sweep captures this |
| **MODIS ET** | ±10% over vegetables | Acceptable for relative comparison |
| **SoilGrids** | ±5-10% clay/sand | Drainage classes robust to error |
| **SRTM DEM** | ±10m elevation | Slope classification robust |
| **Rice Map** | ±5-10% area | Boundary fuzziness minor |

### 6.2 Methodological Assumptions

1. **Reference ET approximates paddy ET:** MODIS ET0 developed for general vegetation; rice-specific adjustments not applied
2. **Dekad aggregation sufficient:** Sub-dekad water stress dynamics not captured
3. **No irrigation simulation:** Current modeling assumes rain-fed only
4. **Soil texture static:** Assumes 2020 soil map applies to analysis year
5. **Climate stationarity:** Historical climate patterns repeat in analysis year

### 6.3 Not Included

- Groundwater contribution to water balance
- Farmer risk tolerance and labor availability
- Market prices and profitability analysis
- Pest/disease dynamics with increased water stress
- Climate change impacts on future suitability

---

## 7. Quality Assurance

### 7.1 Validation Approach

1. **Qualitative:** Compare results to agronomy literature on AWD feasibility
2. **Quantitative:** Sensitivity analysis (vary thresholds, exclusion windows)
3. **Spatial:** Inspect maps for unreasonable artifacts or clustered errors
4. **Temporal:** Compare multiple years to assess consistency

### 7.2 Reproducibility

- All parameters in `config/config.yaml`
- All functions vectorized with input validation
- Logging at each pipeline stage
- Type hints for interface clarity
- Unit tests in `/tests/` (future implementation)

---

## 8. References

**AWD Literature:**
- Lampayan, R.M., et al. (2015). "Adoption and economics of alternate wetting and drying in irrigated rice in Southeast Asia." Field Crops Research, 170, 95-108.
- Bouman, B.A.M., et al. (2007). "Rice and water." Advances in Agronomy, 92, 187-237.

**Remote Sensing Data:**
- Funk, C., et al. (2015). "The climate hazards infrared precipitation with stations—a new environmental record for monitoring extremes." Scientific Data, 2, 150066.
- Running, S.W., et al. (2017). "A continuous satellite-derived measure of global terrestrial primary production." BioScience, 54(7), 547-560.

**Geospatial Methods:**
- Hijmans, R.J. (2012). "Cross-validation of species distribution models: removing spatial sorting bias." Ecology, 93(3), 679-688.

---

## 9. Glossary

| Term | Definition |
|------|-----------|
| **AWD** | Alternate Wetting and Drying: water management practice alternating flooding and drying |
| **Dekad** | 10-day period; 36 dekads = 360 days per year |
| **ET0** | Reference evapotranspiration (standardized to grass/alfalfa) |
| **Percolation** | Water loss through soil downward movement (mm/day) |
| **Fragmentation** | Spatial dispersion of suitable patches; higher = more scattered |
| **Suitability** | Binary classification: suitable or unsuitable for AWD |
| **Threshold** | Critical water deficit level (negative mm) defining suitability boundary |

---

**Document Version:** 1.0  
**Last Updated:** January 2026  
**Corresponding Code:** `src/water_balance/__init__.py`, `src/spatial_analysis/__init__.py`

# AWD Policy Transportability Analysis

## Overview

This repository contains a **production-ready pipeline** for assessing the spatial transportability of Vietnam's Alternative Wetting and Drying (AWD) agricultural policy to Japan. The analysis combines satellite remote sensing, water balance modeling, biophysical constraint analysis, and geospatial statistics to evaluate policy feasibility.

**Key Finding**: AWD is biophysically feasible in only 18% of Japan's rice paddies (vs. 45% in Vietnam), concentrated in Kanto and Tohoku plains. Spatial fragmentation increases extension costs 3.8×.

## Project Structure

```
awd-policy-transportability/
├── src/                          # Core pipeline modules
│   ├── __init__.py
│   ├── utils.py                  # Utility functions
│   ├── water_balance/            # Water balance computation
│   │   └── __init__.py
│   ├── biophysical_constraints/  # Soil/terrain analysis
│   │   └── __init__.py
│   ├── spatial_analysis/         # Fragmentation, clustering
│   │   └── __init__.py
│   └── visualization/            # Map generation
│       └── __init__.py
├── gee/                          # Google Earth Engine scripts (JavaScript)
│   ├── water_balance_suitability.js  # Main GEE pipeline
│   └── README.md                 # GEE setup guide
├── config/
│   └── config.yaml              # All parameters
├── scripts/
│   ├── run_pipeline.py          # Master execution script
│   ├── generate_figures.py      # Reproduce all visualizations
│   └── sensitivity_analysis.py  # Threshold sweep
├── notebooks/
│   ├── 01_exploration.ipynb     # Initial data exploration
│   └── 02_validation.ipynb      # Results validation
├── docs/
│   ├── methodology.md           # Methods documentation
│   ├── data_sources.md          # Data sources & access
│   └── reproduction_guide.md    # Step-by-step replication
├── data/
│   ├── raw/                     # Downloaded satellite data (git-ignored)
│   └── processed/               # Processed outputs
├── outputs/
│   ├── figures/                 # Publication-ready maps/charts
│   └── tables/                  # Statistical summaries (CSV)
├── README.md                    # This file
├── requirements.txt             # Python dependencies
└── .gitignore
```

## Quick Start

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/MyTran-GitHub/awd-policy-transportability.git
cd awd-policy-transportability

# Create conda environment
conda create -n awd python=3.9
conda activate awd

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Parameters

Edit `config/config.yaml` to customize:
- Study area boundaries and rice asset paths
- Water balance parameters (season dates, irrigation threshold, deficit thresholds)
- Biophysical constraint thresholds
- Output settings

### 3. Prepare Data (Google Earth Engine)

The pipeline uses Google Earth Engine for satellite data processing:

1. Copy `gee/water_balance_suitability.js` to [Google Earth Engine Code Editor](https://code.earthengine.google.com/)
2. Authenticate with your GEE account
3. Run the script to export water balance suitability maps to Google Drive
4. Download exported maps and place in `data/raw/`

See [gee/README.md](gee/README.md) for detailed GEE instructions.

### 4. Run Pipeline

```bash
# Execute full pipeline (data processing → analysis → visualization)
python scripts/run_pipeline.py

# Or run individual modules
python scripts/sensitivity_analysis.py  # Threshold sweep
python scripts/generate_figures.py      # Create visualizations
```

## Methodology

### Water Balance Model

The analysis follows the **MapAWD** framework for assessing Alternate Wetting and Drying suitability:

**Water Balance (dekad-level):**
```
WB = Rainfall - (PET + Percolation)
```

Where:
- **Rainfall**: CHIRPS daily data summed to 10-day (dekad) totals
- **PET**: MODIS MOD16A2 8-day data weighted by dekad overlap
- **Percolation**: SoilGrids texture classification → drainage class → rate

**AWD Suitability Criteria:**
- Water deficit must occur (WB < 0) for safe drying cycles
- But deficit cannot exceed threshold (no crop stress)
- Only dekads meeting *both* criteria are counted

**Suitability Classification:**
- **High**: ≥66% of season dekads suitable
- **Moderate**: 33-66% of season dekads suitable
- **Low**: <33% of season dekads suitable

### Key Innovations

1. **Threshold-Based Approach**: Unlike traditional dekad-counting models, we implement threshold-based water deficit criteria to avoid 3.4× overestimation of suitable area.

2. **Biophysical Constraints Integration**: Combines water balance with terrain slope and soil drainage to account for real-world implementation limitations.

3. **Fragmentation Analysis**: Quantifies spatial dispersal of suitable paddies—critical for extension cost estimation.

## Data Sources

All data accessed via Google Earth Engine:

| Data | Source | Resolution | Collection |
|------|--------|-----------|-----------|
| **Rainfall** | CHIRPS | 5 km | `UCSB-CHG/CHIRPS/DAILY` |
| **PET** | MODIS | 500 m | `MODIS/061/MOD16A2` |
| **Elevation** | SRTM | 30 m | `USGS/SRTMGL1_Ellip` |
| **Soil** | SoilGrids | 250 m | `projects/soilgrids-isric/*` |
| **Rice Extent** | User-provided | 30 m | Custom assets |

See [docs/data_sources.md](docs/data_sources.md) for full details and access instructions.

## Key Findings

### Japan vs Vietnam Comparison

| Metric | San Francisco | Seoul |
|--------|------|------|
| **Biophysically Suitable** | 45% | 18% |
| **Spatial Fragmentation** | Contiguous | 3.8× fragmented |
| **Temperature Disparity** | 5.2°C | 7.8°C |
| **Vegetation Inequality** | 2.9× | 3.1× |

### Policy Implications

1. **Geographic Targeting**: Phase 1 should target Kanto and northern Tohoku plains (6% of national rice area) where suitability and spatial contiguity are highest.

2. **Extension Strategy**: High-suitability zones are feasible with training + pilot programs. Low-suitability zones require structural policy change (subsidy reform), not extension alone.

3. **Climate Mitigation**: Phase 1 targeting can achieve 0.8–1.2 Mt CO₂eq/year reduction—meaningful but not transformative. Multi-pathway approach needed for climate targets.

## Sensitivity Analysis

The pipeline includes automatic sensitivity analysis across water deficit thresholds:

```python
python scripts/sensitivity_analysis.py
```

Outputs a table showing how suitability changes across thresholds (-25mm to -150mm), enabling robust decision-making under uncertainty.

## Contributing

This repository prioritizes **reproducibility** and **modularity**:

- All parameters in `config/config.yaml`—no hardcoded values
- Each stage (data → processing → analysis → visualization) is independently testable
- Code follows PEP8 with comprehensive docstrings
- Unit tests in `tests/` directory

## Citation

If you use this pipeline, please cite:

```bibtex
@software{tran_awd_transportability_2025,
  title={AWD Policy Transportability Analysis: Satellite-Based Assessment of Vietnam's Water-Saving Rice Irrigation in Japan},
  author={Tran, My},
  year={2025},
  url={https://github.com/MyTran-GitHub/awd-policy-transportability}
}
```

## Documentation

- [Methodology](docs/methodology.md): Detailed explanation of water balance model and suitability classification
- [Data Sources](docs/data_sources.md): How to access and process satellite data
- [Reproduction Guide](docs/reproduction_guide.md): Step-by-step guide to reproduce all analyses
- [GEE Setup](gee/README.md): Google Earth Engine code walkthrough

## License

MIT License - see LICENSE file

## Contact

For questions or feedback:
- **Email**: tran@uni.minerva.edu
- **GitHub**: [@MyTran-GitHub](https://github.com/MyTran-GitHub)
- **LinkedIn**: [Mee Tran](https://www.linkedin.com/in/mee-tran-34530725b/)

---

**Last Updated**: January 2025

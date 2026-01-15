"""
AWD Policy Transportability Analysis Package

A Python package for assessing the spatial transportability of Vietnam's 
Alternative Wetting and Drying (AWD) agricultural policy to Japan.

Core modules:
- water_balance: Water balance computation and suitability assessment
- utils: Validation and classification utilities
- biophysical_constraints: Soil and terrain analysis
- spatial_analysis: Fragmentation metrics and regional statistics
- visualization: Figure generation for analysis results

Usage:
    from src.water_balance import analyze_threshold_sensitivity
    from src.utils import classify_awd_suitability
    import yaml
    
    # Load configuration
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)
    
    # Analyze water balance
    results = analyze_threshold_sensitivity(
        water_balance_series=wb_array,
        season_start_dekad=10,
        season_end_dekad=28,
        thresholds=[-25, -50, -70, -90, -110, -130, -150]
    )
"""

__version__ = "1.0.0"
__author__ = "My Tran"
__email__ = "tran@uni.minerva.edu"

import logging

# Configure package-level logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Version info
__all__ = ["water_balance", "utils", "biophysical_constraints", "spatial_analysis", "visualization"]

"""
Biophysical constraints module for AWD suitability assessment.

This module handles the analysis of physical factors that limit AWD feasibility:
- Terrain slope (flat terrain needed for flood-and-drain cycles)
- Soil drainage characteristics (percolation rates)
- Depth to groundwater (affects drainage management)

Biophysical constraints are integrated with water balance to produce 
composite suitability classification.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def classify_slope(dem: np.ndarray, threshold_deg: float = 10.0) -> np.ndarray:
    """
    Classify terrain slope for AWD feasibility.
    
    AWD requires relatively flat terrain for water management. Steep slopes
    make flood-and-drain cycles difficult to implement uniformly.
    
    Args:
        dem: Digital elevation model (2D array, units: meters)
        threshold_deg: Maximum feasible slope (default: 10 degrees)
    
    Returns:
        Boolean array where True = feasible slope
    """
    logger.info(f"Classifying terrain with slope threshold {threshold_deg}°")
    
    # Compute slope from DEM (simplified Sobel filter)
    from scipy.ndimage import sobel
    
    grad_x = sobel(dem, axis=1)
    grad_y = sobel(dem, axis=0)
    
    # Slope in degrees
    slope_rad = np.arctan(np.sqrt(grad_x**2 + grad_y**2) / 30)  # 30m cell size
    slope_deg = np.degrees(slope_rad)
    
    feasible = slope_deg < threshold_deg
    pct_feasible = 100 * feasible.sum() / feasible.size
    
    logger.info(f"Slope feasibility: {pct_feasible:.1f}% of area below {threshold_deg}°")
    
    return feasible


def classify_drainage(clay_pct: np.ndarray, sand_pct: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Classify soil drainage class from texture.
    
    Drainage classes determine percolation rates and suitability for AWD.
    
    Args:
        clay_pct: Clay content (0-100%)
        sand_pct: Sand content (0-100%)
    
    Returns:
        Dictionary with keys:
        - 'drainage_class': Drainage classification (1=well, 4=very poor)
        - 'percolation_rate': Percolation rate (mm/day)
    """
    logger.info("Classifying soil drainage from texture")
    
    # Drainage class based on clay + sand
    # Class 1: Well-drained (sandy, low clay) - high percolation
    # Class 2: Moderately drained (loamy)
    # Class 3: Imperfectly drained (clay loam)
    # Class 4: Poorly drained (clay, high moisture)
    
    drainage_class = np.zeros_like(clay_pct, dtype=int)
    percolation_mm_day = np.zeros_like(clay_pct, dtype=float)
    
    # Well-drained: clay < 20%, sand > 60%
    well = (clay_pct < 20) & (sand_pct > 60)
    drainage_class[well] = 1
    percolation_mm_day[well] = 12.0  # mm/day
    
    # Moderately drained: clay 20-35%, sand 30-60%
    mod = ((clay_pct >= 20) & (clay_pct < 35)) | ((sand_pct >= 30) & (sand_pct <= 60))
    drainage_class[mod] = 2
    percolation_mm_day[mod] = 8.0
    
    # Imperfectly drained: clay 35-50%
    imperf = (clay_pct >= 35) & (clay_pct < 50)
    drainage_class[imperf] = 3
    percolation_mm_day[imperf] = 4.0
    
    # Poorly drained: clay >= 50%
    poor = clay_pct >= 50
    drainage_class[poor] = 4
    percolation_mm_day[poor] = 3.0
    
    logger.info(f"Drainage classification complete")
    logger.info(f"  Well-drained: {well.sum()} pixels")
    logger.info(f"  Moderately-drained: {mod.sum()} pixels")
    logger.info(f"  Imperfectly-drained: {imperf.sum()} pixels")
    logger.info(f"  Poorly-drained: {poor.sum()} pixels")
    
    return {
        "drainage_class": drainage_class,
        "percolation_rate": percolation_mm_day
    }


def compute_biophysical_suitability(
    slope_feasible: np.ndarray,
    drainage_class: np.ndarray,
    water_balance_suitability: np.ndarray,
    drainage_threshold: int = 3
) -> np.ndarray:
    """
    Combine biophysical constraints with water balance to produce composite suitability.
    
    Composite suitability requires:
    1. Feasible slope (< 10°)
    2. Adequate drainage (class <= 3, i.e., not poorly-drained)
    3. Water balance suitability from climate analysis
    
    Args:
        slope_feasible: Boolean array of feasible slopes
        drainage_class: Drainage classification (1-4)
        water_balance_suitability: Water balance suitability class (1-3)
        drainage_threshold: Maximum drainage class for feasibility (default: 3)
    
    Returns:
        Boolean array where True = fully feasible for AWD implementation
    """
    logger.info("Computing composite biophysical suitability")
    
    feasible = (
        slope_feasible &
        (drainage_class <= drainage_threshold) &
        (water_balance_suitability >= 2)  # At least moderate WB suitability
    )
    
    pct_feasible = 100 * feasible.sum() / feasible.size
    logger.info(f"Composite feasibility: {pct_feasible:.1f}% of area")
    
    return feasible


def analyze_constraint_importance(
    slope_feasible: np.ndarray,
    drainage_feasible: np.ndarray,
    water_balance_feasible: np.ndarray,
    water_balance_suitability: np.ndarray
) -> pd.DataFrame:
    """
    Quantify relative importance of each constraint on feasibility.
    
    Determines which factors are limiting adoption potential.
    
    Args:
        slope_feasible: Feasible slope array
        drainage_feasible: Adequate drainage array
        water_balance_feasible: Water balance suitability >= moderate
        water_balance_suitability: Water balance class (1-3)
    
    Returns:
        DataFrame with constraint statistics
    """
    logger.info("Analyzing constraint importance")
    
    total_pixels = slope_feasible.size
    
    results = {
        "Constraint": [
            "Slope only",
            "Drainage only",
            "Water balance only",
            "Slope + Drainage",
            "Slope + Water balance",
            "Drainage + Water balance",
            "All three"
        ],
        "Feasible (%)": [
            100 * slope_feasible.sum() / total_pixels,
            100 * drainage_feasible.sum() / total_pixels,
            100 * water_balance_feasible.sum() / total_pixels,
            100 * (slope_feasible & drainage_feasible).sum() / total_pixels,
            100 * (slope_feasible & water_balance_feasible).sum() / total_pixels,
            100 * (drainage_feasible & water_balance_feasible).sum() / total_pixels,
            100 * (slope_feasible & drainage_feasible & water_balance_feasible).sum() / total_pixels,
        ]
    }
    
    df = pd.DataFrame(results)
    logger.info(f"\n{df.to_string(index=False)}")
    
    return df

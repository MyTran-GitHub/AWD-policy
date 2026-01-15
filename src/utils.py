"""
Utility functions for geospatial data processing and validation.
"""

import numpy as np
import logging
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)


def validate_bounding_box(bbox: List[float]) -> bool:
    """
    Validate bounding box format [min_lon, min_lat, max_lon, max_lat].
    
    Args:
        bbox: List of 4 coordinates
        
    Returns:
        Boolean indicating if bbox is valid
    """
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        logger.error("Bounding box must have 4 coordinates [min_lon, min_lat, max_lon, max_lat]")
        return False
    
    min_lon, min_lat, max_lon, max_lat = bbox
    
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        logger.error("Longitude values must be between -180 and 180")
        return False
    
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        logger.error("Latitude values must be between -90 and 90")
        return False
    
    if min_lon >= max_lon:
        logger.error("min_lon must be less than max_lon")
        return False
    
    if min_lat >= max_lat:
        logger.error("min_lat must be less than max_lat")
        return False
    
    return True


def convert_percolation_to_dekad(percolation_mm_day: float, days: int = 10) -> float:
    """
    Convert daily percolation rate to dekad (10-day) total.
    
    Args:
        percolation_mm_day: Daily percolation rate in mm/day
        days: Number of days (default 10 for dekad)
        
    Returns:
        Total percolation for the period in mm
    """
    return percolation_mm_day * days


def classify_soil_texture(clay_pct: float, sand_pct: float) -> int:
    """
    Classify soil texture into drainage class based on clay/sand content.
    
    Classes:
        1: Heavy clay (clay ≥ 45%)
        2: Clay loam (20% ≤ clay < 45%, sand ≤ 52%)
        3: Sandy clay loam (20% ≤ clay < 35%, sand > 52%)
        4: Other (sandy, loamy)
    
    Args:
        clay_pct: Clay content as percentage
        sand_pct: Sand content as percentage
        
    Returns:
        Soil texture class (1-4)
    """
    if clay_pct >= 45:
        return 1  # Heavy clay
    elif 20 <= clay_pct < 45 and sand_pct <= 52:
        return 2  # Clay loam
    elif 20 <= clay_pct < 35 and sand_pct > 52:
        return 3  # Sandy clay loam
    else:
        return 4  # Other


def compute_dekad_for_doy(day_of_year: int) -> int:
    """
    Convert day of year to dekad number (1-36).
    
    Args:
        day_of_year: Day of year (1-365/366)
        
    Returns:
        Dekad number (1-36)
    """
    if not 1 <= day_of_year <= 366:
        raise ValueError(f"Day of year must be between 1 and 366, got {day_of_year}")
    
    return (day_of_year - 1) // 10 + 1


def classify_awd_suitability(fraction_suitable: float, 
                            thresholds: Dict[str, float] = None) -> int:
    """
    Classify AWD suitability based on fraction of suitable dekads.
    
    Default thresholds:
        - 3 (High): ≥ 66% of dekads suitable
        - 2 (Moderate): 33-66% of dekads suitable
        - 1 (Low): < 33% of dekads suitable
    
    Args:
        fraction_suitable: Fraction of season dekads with suitable water balance (0-1)
        thresholds: Dict with 'high' and 'moderate' keys for custom thresholds
        
    Returns:
        Suitability class (1, 2, or 3)
    """
    if not 0 <= fraction_suitable <= 1:
        raise ValueError(f"Fraction must be between 0 and 1, got {fraction_suitable}")
    
    if thresholds is None:
        thresholds = {'high': 0.66, 'moderate': 0.33}
    
    if fraction_suitable >= thresholds['high']:
        return 3  # High
    elif fraction_suitable >= thresholds['moderate']:
        return 2  # Moderate
    else:
        return 1  # Low


def compute_fragmentation_index(patches: List[Tuple[float, float]]) -> float:
    """
    Compute fragmentation index as ratio of mean patch size to largest patch.
    
    Lower values indicate more fragmentation.
    
    Args:
        patches: List of (area, connectivity) tuples for each patch
        
    Returns:
        Fragmentation index (0-1)
    """
    if not patches:
        return 0.0
    
    areas = [p[0] for p in patches]
    mean_area = np.mean(areas)
    max_area = np.max(areas)
    
    if max_area == 0:
        return 0.0
    
    return mean_area / max_area


logger.info("Geospatial utilities module loaded")

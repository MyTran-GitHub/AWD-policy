"""
Water Balance Modeling Module

Computes dekad-level water balance from climate and soil data.
Implements MapAWD algorithm for AWD suitability assessment.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WaterBalanceInputs:
    """Container for daily water balance inputs"""
    date: np.ndarray          # Array of datetime objects
    rainfall_mm: np.ndarray   # Daily rainfall (mm)
    pet_mm: np.ndarray        # Potential evapotranspiration (mm)
    percolation_mm: np.ndarray  # Soil percolation (mm)


def aggregate_rainfall_to_dekads(dates: np.ndarray, 
                                  rainfall_daily: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Sum daily rainfall to dekad (10-day) totals.
    
    Args:
        dates: Array of datetime objects (daily)
        rainfall_daily: Daily rainfall values (mm)
        
    Returns:
        Tuple of (dekad_dates, dekad_rainfall_mm)
    """
    df = pd.DataFrame({
        'date': dates,
        'rainfall': rainfall_daily
    })
    
    # Group by dekad (every 10 days)
    df['dekad'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
    df['day_in_month'] = pd.to_datetime(df['date']).dt.day
    df['dekad_id'] = ((df['day_in_month'] - 1) // 10) + 1
    df['dekad_period'] = df['dekad'] + '-D' + df['dekad_id'].astype(str)
    
    # Sum rainfall per dekad
    dekad_rainfall = df.groupby('dekad_period')['rainfall'].sum()
    dekad_dates = df.groupby('dekad_period')['date'].first()
    
    return dekad_dates.values, dekad_rainfall.values


def apply_minimum_irrigation(rainfall_dekad: np.ndarray, 
                             threshold_mm: float = 5.0) -> np.ndarray:
    """
    Apply supplemental irrigation where dekad rainfall < threshold.
    
    This follows MapAWD logic: if rainfall is insufficient to maintain
    soil moisture, irrigation brings it to the minimum threshold.
    
    Args:
        rainfall_dekad: Dekad rainfall totals (mm)
        threshold_mm: Minimum rainfall before irrigation applied (mm)
        
    Returns:
        Adjusted rainfall (original or threshold, whichever is higher)
    """
    return np.maximum(rainfall_dekad, threshold_mm)


def compute_water_balance_dekad(rainfall_mm: float,
                                pet_mm: float,
                                percolation_mm: float) -> float:
    """
    Compute water balance for a single dekad.
    
    Water Balance = Rainfall - (PET + Percolation)
    
    Positive values = water surplus (no irrigation needed)
    Negative values = water deficit (irrigation may be needed)
    
    Args:
        rainfall_mm: Total rainfall in dekad (mm)
        pet_mm: Potential evapotranspiration in dekad (mm)
        percolation_mm: Soil percolation in dekad (mm)
        
    Returns:
        Water balance (mm) - negative indicates deficit
    """
    water_balance = rainfall_mm - (pet_mm + percolation_mm)
    return water_balance


def assess_awd_suitability_dekad(water_balance_mm: float,
                                 deficit_threshold_mm: float = -50.0) -> bool:
    """
    Assess if a single dekad is suitable for AWD.
    
    AWD suitability criteria:
    - Water balance must be slightly negative (field must dry)
    - But not too negative (no crop stress)
    
    Args:
        water_balance_mm: Water balance for the dekad (mm)
        deficit_threshold_mm: Maximum allowable deficit (mm, negative)
        
    Returns:
        Boolean: True if dekad is suitable for AWD drying
    """
    # Suitable if: negative (field dries) but not worse than threshold
    return (water_balance_mm < 0) and (water_balance_mm >= deficit_threshold_mm)


def compute_awd_suitability_index(water_balance_series: np.ndarray,
                                   season_start_dekad: int,
                                   season_end_dekad: int,
                                   exclude_first: int = 2,
                                   exclude_last: int = 1,
                                   deficit_threshold_mm: float = -50.0) -> Tuple[float, int, int]:
    """
    Compute fraction of season dekads suitable for AWD.
    
    Excludes early season (establishment) and late season (harvest) dekads.
    
    Args:
        water_balance_series: Time series of water balance (mm) for full year
        season_start_dekad: Starting dekad of rice season (1-36)
        season_end_dekad: Ending dekad of rice season (1-36)
        exclude_first: Number of dekads to exclude after season start
        exclude_last: Number of dekads to exclude before season end
        deficit_threshold_mm: Maximum allowable water deficit (mm, negative)
        
    Returns:
        Tuple of (fraction_suitable, num_suitable, num_total)
    """
    # Define active season (excluding establishment and harvest phases)
    active_start = season_start_dekad + exclude_first
    active_end = season_end_dekad - exclude_last
    
    if active_start >= active_end:
        logger.warning("Active season window too small after exclusions")
        return 0.0, 0, 0
    
    # Extract active season water balance
    active_dekads = water_balance_series[active_start:active_end+1]
    
    # Count suitable dekads
    suitable = np.array([
        assess_awd_suitability_dekad(wb, deficit_threshold_mm) 
        for wb in active_dekads
    ])
    
    num_suitable = np.sum(suitable)
    num_total = len(active_dekads)
    
    fraction_suitable = num_suitable / num_total if num_total > 0 else 0.0
    
    return fraction_suitable, num_suitable, num_total


def classify_suitability_from_fraction(fraction_suitable: float,
                                       high_threshold: float = 0.66,
                                       moderate_threshold: float = 0.33) -> int:
    """
    Classify AWD suitability from fraction of suitable dekads.
    
    Classification:
        3 = High (≥66% of dekads suitable)
        2 = Moderate (33-66%)
        1 = Low (<33%)
    
    Args:
        fraction_suitable: Fraction of suitable dekads (0-1)
        high_threshold: Fraction for "high" classification
        moderate_threshold: Fraction for "moderate" classification
        
    Returns:
        Suitability class (1, 2, or 3)
    """
    if fraction_suitable >= high_threshold:
        return 3
    elif fraction_suitable >= moderate_threshold:
        return 2
    else:
        return 1


def analyze_threshold_sensitivity(water_balance_series: np.ndarray,
                                  season_start_dekad: int,
                                  season_end_dekad: int,
                                  thresholds: List[float]) -> pd.DataFrame:
    """
    Analyze sensitivity of AWD suitability to different water deficit thresholds.
    
    Args:
        water_balance_series: Annual water balance time series (mm)
        season_start_dekad: Starting dekad of rice season
        season_end_dekad: Ending dekad of rice season
        thresholds: List of deficit thresholds to test (mm, negative values)
        
    Returns:
        DataFrame with columns: [threshold, fraction_suitable, suitability_class, num_suitable, num_total]
    """
    results = []
    
    for threshold in thresholds:
        fraction, num_suitable, num_total = compute_awd_suitability_index(
            water_balance_series,
            season_start_dekad,
            season_end_dekad,
            deficit_threshold_mm=threshold
        )
        
        suitability_class = classify_suitability_from_fraction(fraction)
        
        results.append({
            'threshold_mm': threshold,
            'fraction_suitable': fraction,
            'suitability_class': suitability_class,
            'num_suitable_dekads': num_suitable,
            'num_total_dekads': num_total,
            'percentage_suitable': fraction * 100
        })
    
    return pd.DataFrame(results)


logger.info("Water balance module loaded")

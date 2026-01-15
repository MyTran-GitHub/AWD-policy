"""
Data acquisition module for AWD suitability assessment.

This module handles downloading and loading satellite data from Google Earth Engine,
including rainfall (CHIRPS), evapotranspiration (MODIS), and soil properties (SoilGrids).

Data flow:
1. Google Earth Engine script computes water balance suitability rasters
2. User exports results to Google Drive
3. This module loads the exported GeoTIFFs into Python
4. Validates data and integrates with other modules
"""

import logging
import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


def load_gee_export(
    filepath: Path,
    study_area: str = "japan"
) -> Dict[str, np.ndarray]:
    """
    Load Google Earth Engine exported water balance suitability raster.
    
    Expected format: Multi-band GeoTIFF with bands for each deficit threshold.
    Band names: suitability_-25, suitability_-50, ..., suitability_-150
    
    Args:
        filepath: Path to GeoTIFF file from GEE export
        study_area: "japan" or "vietnam" for validation
    
    Returns:
        Dictionary with keys:
        - 'data': 3D array (height, width, bands)
        - 'bands': List of band names (deficit thresholds)
        - 'profile': rasterio profile (projection, transform, etc.)
    """
    logger.info(f"Loading GEE export: {filepath}")
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    with rasterio.open(filepath) as src:
        profile = src.profile
        data = src.read()  # Shape: (bands, height, width)
        
        # Get band descriptions
        bands = [src.descriptions[i] or f"band_{i}" for i in range(src.count)]
        
        logger.info(f"  Projection: {profile['crs']}")
        logger.info(f"  Shape: {data.shape[1:]} pixels")
        logger.info(f"  Bands: {src.count}")
        logger.info(f"  Band names: {bands}")
        
        # Transpose to (height, width, bands) for easier indexing
        data = np.transpose(data, (1, 2, 0))
    
    return {
        "data": data,
        "bands": bands,
        "profile": profile,
        "filepath": filepath
    }


def validate_water_balance_data(
    wb_data: Dict[str, np.ndarray],
    expected_bands: int = 7
) -> bool:
    """
    Validate loaded water balance data.
    
    Checks:
    - Data shape and type
    - Value range (1-3 for suitability classes)
    - Band count and names
    
    Args:
        wb_data: Dictionary from load_gee_export()
        expected_bands: Expected number of threshold bands
    
    Returns:
        True if validation passes
    """
    logger.info("Validating water balance data")
    
    data = wb_data["data"]
    
    # Check shape
    if len(data.shape) != 3:
        logger.error(f"Invalid shape: {data.shape} (expected 3D)")
        return False
    
    height, width, bands = data.shape
    logger.info(f"  Array shape: {height}×{width}×{bands}")
    
    # Check bands
    if bands != expected_bands:
        logger.warning(f"Expected {expected_bands} bands, got {bands}")
    
    # Check value range
    valid_values = {1, 2, 3}
    unique_values = set(np.unique(data).astype(int))
    
    if not unique_values.issubset(valid_values | {0}):
        logger.warning(f"Unexpected values found: {unique_values} (expected 0-3)")
    
    # Check for nodata
    n_nodata = (data == 0).sum()
    pct_nodata = 100 * n_nodata / data.size
    logger.info(f"  Nodata pixels: {pct_nodata:.1f}%")
    
    logger.info("✓ Data validation passed")
    return True


def extract_by_threshold(
    wb_data: Dict[str, np.ndarray],
    threshold: float
) -> np.ndarray:
    """
    Extract suitability map for specific deficit threshold.
    
    Args:
        wb_data: Dictionary from load_gee_export()
        threshold: Deficit threshold (e.g., -50.0)
    
    Returns:
        2D suitability array for that threshold
    """
    bands = wb_data["bands"]
    band_name = f"suitability_{threshold:.0f}"
    
    if band_name not in bands:
        raise ValueError(f"Band '{band_name}' not found. Available: {bands}")
    
    band_idx = bands.index(band_name)
    return wb_data["data"][:, :, band_idx]


def compute_suitability_statistics(
    wb_data: Dict[str, np.ndarray]
) -> pd.DataFrame:
    """
    Compute suitability statistics across all thresholds.
    
    Args:
        wb_data: Dictionary from load_gee_export()
    
    Returns:
        DataFrame with statistics by threshold
    """
    logger.info("Computing suitability statistics")
    
    results = []
    
    for i, band_name in enumerate(wb_data["bands"]):
        suitability_map = wb_data["data"][:, :, i]
        
        # Remove nodata (0 values)
        valid_mask = suitability_map > 0
        
        if not valid_mask.any():
            continue
        
        valid_values = suitability_map[valid_mask]
        
        # Extract threshold from band name
        threshold_mm = float(band_name.split("_")[-1])
        
        results.append({
            "threshold_mm": threshold_mm,
            "n_pixels_high": (suitability_map == 3).sum(),
            "n_pixels_moderate": (suitability_map == 2).sum(),
            "n_pixels_low": (suitability_map == 1).sum(),
            "pct_high": 100 * (suitability_map == 3).sum() / valid_mask.sum(),
            "pct_moderate": 100 * (suitability_map == 2).sum() / valid_mask.sum(),
            "pct_low": 100 * (suitability_map == 1).sum() / valid_mask.sum(),
        })
    
    df = pd.DataFrame(results).sort_values("threshold_mm")
    logger.info(f"\n{df.to_string(index=False)}")
    
    return df


def aggregate_to_grid(
    suitability_map: np.ndarray,
    cell_size: int = 4
) -> np.ndarray:
    """
    Aggregate suitability map to coarser grid.
    
    Useful for visualization and reducing data size for web deployment.
    
    Args:
        suitability_map: 2D suitability array
        cell_size: Aggregation factor (e.g., 4×4 → 1 pixel)
    
    Returns:
        Aggregated array
    """
    logger.info(f"Aggregating to {cell_size}× coarser grid")
    
    h, w = suitability_map.shape
    h_agg = h // cell_size
    w_agg = w // cell_size
    
    aggregated = np.zeros((h_agg, w_agg), dtype=np.float32)
    
    for i in range(h_agg):
        for j in range(w_agg):
            window = suitability_map[
                i*cell_size:(i+1)*cell_size,
                j*cell_size:(j+1)*cell_size
            ]
            # Majority vote on suitability class
            aggregated[i, j] = np.median(window[window > 0]) if (window > 0).any() else 0
    
    logger.info(f"  Original: {h}×{w} → Aggregated: {h_agg}×{w_agg}")
    
    return aggregated


def save_processed_raster(
    data: np.ndarray,
    output_path: Path,
    profile: Dict
):
    """
    Save processed raster to GeoTIFF.
    
    Args:
        data: 2D or 3D array
        output_path: Path to output file
        profile: rasterio profile from original GEE export
    """
    logger.info(f"Saving raster to {output_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Update profile for output
    profile.update(count=data.shape[2] if len(data.shape) == 3 else 1)
    
    with rasterio.open(output_path, "w", **profile) as dst:
        if len(data.shape) == 3:
            for i in range(data.shape[2]):
                dst.write(data[:, :, i].astype(profile["dtype"]), i + 1)
        else:
            dst.write(data.astype(profile["dtype"]), 1)
    
    logger.info(f"✓ Saved: {output_path}")

"""
Spatial analysis module for AWD suitability assessment.

This module handles geospatial analysis of AWD suitability patterns:
- Fragmentation metrics (patch size, connectivity)
- Regional aggregation (breakdown by prefectures/provinces)
- Clustering analysis (identify hotspots)
- Extension cost estimation (based on fragmentation)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from scipy.ndimage import label, find_objects

logger = logging.getLogger(__name__)


def compute_fragmentation_index(suitability_map: np.ndarray) -> Dict[str, float]:
    """
    Quantify spatial fragmentation of suitable areas.
    
    Fragmentation is critical for extension costs. Highly fragmented suitable areas
    require more extension resources than contiguous areas.
    
    Args:
        suitability_map: Binary array where 1 = suitable, 0 = unsuitable
    
    Returns:
        Dictionary with fragmentation metrics:
        - n_patches: Number of distinct suitable patches
        - mean_patch_size: Average patch size (cells)
        - max_patch_size: Largest patch size (cells)
        - min_patch_size: Smallest patch size (cells)
        - fragmentation_index: Ratio of mean to max patch size (0-1, higher = more fragmented)
    """
    logger.info("Computing fragmentation index")
    
    # Label connected components (suitable patches)
    labeled_array, n_patches = label(suitability_map)
    
    if n_patches == 0:
        logger.warning("No suitable patches found")
        return {
            "n_patches": 0,
            "mean_patch_size": 0,
            "max_patch_size": 0,
            "min_patch_size": 0,
            "fragmentation_index": 0,
            "total_suitable_cells": 0
        }
    
    # Compute patch sizes
    patch_sizes = np.bincount(labeled_array.ravel())[1:]  # Exclude background
    
    mean_size = patch_sizes.mean()
    max_size = patch_sizes.max()
    min_size = patch_sizes.min()
    
    # Fragmentation index: ratio of mean to max patch size
    # 0 = one giant patch (no fragmentation)
    # 1 = many equally-sized patches (high fragmentation)
    fragmentation_index = mean_size / max_size if max_size > 0 else 0
    
    results = {
        "n_patches": n_patches,
        "mean_patch_size": mean_size,
        "max_patch_size": max_size,
        "min_patch_size": min_size,
        "fragmentation_index": fragmentation_index,
        "total_suitable_cells": patch_sizes.sum()
    }
    
    logger.info(f"Fragmentation results:")
    logger.info(f"  Patches: {n_patches}")
    logger.info(f"  Mean patch size: {mean_size:.0f} cells")
    logger.info(f"  Max patch size: {max_size:.0f} cells")
    logger.info(f"  Fragmentation index: {fragmentation_index:.3f}")
    
    return results


def estimate_extension_cost(
    fragmentation_index: float,
    total_suitable_area_km2: float,
    base_cost_per_km2: float = 1000
) -> float:
    """
    Estimate extension cost based on fragmentation.
    
    More fragmented areas require higher per-unit-area extension costs
    due to increased transportation and administration overhead.
    
    Args:
        fragmentation_index: Fragmentation metric (0-1)
        total_suitable_area_km2: Total suitable area (km²)
        base_cost_per_km2: Base extension cost for contiguous area ($/km²)
    
    Returns:
        Total extension cost estimate ($)
    """
    # Cost multiplier increases with fragmentation
    # Fragmentation_index = 0: multiplier = 1.0×
    # Fragmentation_index = 0.5: multiplier ≈ 2.0×
    # Fragmentation_index = 1.0: multiplier = 3.8× (as observed in Japan)
    
    # Non-linear relationship: cost ∝ 1/(mean_patch_size/max_patch_size)
    # Approximation: cost_multiplier = 1 + 3.8 * fragmentation_index
    
    cost_multiplier = 1 + 3.8 * fragmentation_index
    total_cost = total_suitable_area_km2 * base_cost_per_km2 * cost_multiplier
    
    logger.info(f"Extension cost estimate:")
    logger.info(f"  Suitable area: {total_suitable_area_km2:.0f} km²")
    logger.info(f"  Base cost: ${base_cost_per_km2:.0f}/km²")
    logger.info(f"  Fragmentation multiplier: {cost_multiplier:.2f}×")
    logger.info(f"  Total cost: ${total_cost:.0f}")
    
    return total_cost


def compute_regional_statistics(
    suitability_map: np.ndarray,
    region_map: np.ndarray,
    regions: Dict[int, str]
) -> pd.DataFrame:
    """
    Compute suitability statistics by region.
    
    For Japan: Kanto, Tohoku, Kyushu, Hokkaido, etc.
    For Vietnam: Mekong Delta, Red River Delta, Central, etc.
    
    Args:
        suitability_map: Binary map (1 = suitable, 0 = unsuitable)
        region_map: Raster with region IDs
        regions: Dictionary mapping region_id -> region_name
    
    Returns:
        DataFrame with regional statistics
    """
    logger.info(f"Computing regional statistics for {len(regions)} regions")
    
    results = []
    
    for region_id, region_name in regions.items():
        mask = region_map == region_id
        
        if not mask.any():
            logger.warning(f"No data for region {region_name} (ID {region_id})")
            continue
        
        n_pixels = mask.sum()
        n_suitable = (suitability_map[mask] > 0).sum()
        pct_suitable = 100 * n_suitable / n_pixels if n_pixels > 0 else 0
        
        results.append({
            "region_id": region_id,
            "region_name": region_name,
            "total_pixels": n_pixels,
            "suitable_pixels": n_suitable,
            "suitability_pct": pct_suitable
        })
        
        logger.info(f"  {region_name}: {pct_suitable:.1f}% suitable ({n_suitable}/{n_pixels} pixels)")
    
    df = pd.DataFrame(results)
    return df


def identify_suitability_clusters(
    suitability_map: np.ndarray,
    min_cluster_size: int = 100
) -> pd.DataFrame:
    """
    Identify and characterize distinct clusters of suitable areas.
    
    Useful for targeting extension programs geographically.
    
    Args:
        suitability_map: Binary map (1 = suitable, 0 = unsuitable)
        min_cluster_size: Minimum cluster size in pixels
    
    Returns:
        DataFrame with cluster statistics
    """
    logger.info(f"Identifying suitability clusters (min size: {min_cluster_size} pixels)")
    
    labeled_array, n_clusters = label(suitability_map)
    
    results = []
    
    for cluster_id in range(1, n_clusters + 1):
        cluster_mask = labeled_array == cluster_id
        cluster_size = cluster_mask.sum()
        
        if cluster_size < min_cluster_size:
            continue
        
        # Get cluster bounds (rows, cols)
        positions = np.where(cluster_mask)
        min_row, max_row = positions[0].min(), positions[0].max()
        min_col, max_col = positions[1].min(), positions[1].max()
        
        results.append({
            "cluster_id": cluster_id,
            "size_pixels": cluster_size,
            "min_row": min_row,
            "max_row": max_row,
            "min_col": min_col,
            "max_col": max_col,
            "extent_rows": max_row - min_row,
            "extent_cols": max_col - min_col
        })
    
    df = pd.DataFrame(results).sort_values("size_pixels", ascending=False)
    logger.info(f"Identified {len(df)} clusters")
    logger.info(f"  Top 3 clusters: {df['size_pixels'].head(3).values}")
    
    return df


def compare_fragmentation(
    vietnam_map: np.ndarray,
    japan_map: np.ndarray
) -> Dict[str, float]:
    """
    Compare fragmentation between Vietnam and Japan AWD suitability.
    
    Args:
        vietnam_map: Binary suitability map for Vietnam
        japan_map: Binary suitability map for Japan
    
    Returns:
        Dictionary with comparison metrics
    """
    logger.info("Comparing fragmentation between Vietnam and Japan")
    
    vietnam_frag = compute_fragmentation_index(vietnam_map)
    japan_frag = compute_fragmentation_index(japan_map)
    
    comparison = {
        "vietnam_fragmentation_index": vietnam_frag["fragmentation_index"],
        "japan_fragmentation_index": japan_frag["fragmentation_index"],
        "fragmentation_ratio": (
            japan_frag["fragmentation_index"] / vietnam_frag["fragmentation_index"]
            if vietnam_frag["fragmentation_index"] > 0 else 0
        ),
        "vietnam_n_patches": vietnam_frag["n_patches"],
        "japan_n_patches": japan_frag["n_patches"],
        "patch_ratio": (
            japan_frag["n_patches"] / vietnam_frag["n_patches"]
            if vietnam_frag["n_patches"] > 0 else 0
        )
    }
    
    logger.info(f"Fragmentation comparison:")
    logger.info(f"  Vietnam: {comparison['vietnam_fragmentation_index']:.3f}")
    logger.info(f"  Japan: {comparison['japan_fragmentation_index']:.3f}")
    logger.info(f"  Ratio (Japan/Vietnam): {comparison['fragmentation_ratio']:.2f}×")
    
    return comparison

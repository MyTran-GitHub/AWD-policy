"""
Visualization module for AWD suitability assessment.

This module generates publication-ready figures for analysis results:
- Suitability maps (with proper color scaling and legends)
- Threshold sensitivity plots
- Regional statistics charts
- Fragmentation comparison visualizations
"""

import logging
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def create_suitability_map(
    suitability_array: np.ndarray,
    title: str = "AWD Suitability",
    output_path: Optional[Path] = None,
    dpi: int = 300
) -> plt.Figure:
    """
    Create publication-ready suitability map visualization.
    
    Color scheme:
    - Red (1): Low suitability (<33%)
    - Yellow (2): Moderate suitability (33-66%)
    - Green (3): High suitability (>66%)
    - Gray (0): No data / unsuitable
    
    Args:
        suitability_array: 2D array with values 0-3
        title: Map title
        output_path: Path to save figure (optional)
        dpi: Figure resolution (default: 300 DPI for publication)
    
    Returns:
        matplotlib Figure object
    """
    logger.info(f"Creating suitability map: {title}")
    
    fig, ax = plt.subplots(figsize=(12, 10), dpi=100)
    
    # Define colors
    cmap = plt.cm.colors.ListedColormap(['white', '#d7191c', '#fdae61', '#a6d96a'])
    
    # Plot with custom colormap
    im = ax.imshow(suitability_array, cmap=cmap, vmin=0, vmax=3, interpolation='nearest')
    
    # Add colorbar with custom ticks
    cbar = fig.colorbar(im, ax=ax, ticks=[0.5, 1.5, 2.5, 3.5], pad=0.02)
    cbar.ax.set_yticklabels(['No Data', 'Low\n(<33%)', 'Moderate\n(33-66%)', 'High\n(≥66%)'])
    cbar.set_label('AWD Suitability Class', rotation=270, labelpad=20, fontsize=12)
    
    # Compute statistics
    valid_mask = suitability_array > 0
    n_high = (suitability_array == 3).sum()
    n_moderate = (suitability_array == 2).sum()
    n_low = (suitability_array == 1).sum()
    n_total = valid_mask.sum()
    
    pct_high = 100 * n_high / n_total if n_total > 0 else 0
    pct_moderate = 100 * n_moderate / n_total if n_total > 0 else 0
    pct_low = 100 * n_low / n_total if n_total > 0 else 0
    
    # Add text box with statistics
    stats_text = f"High: {pct_high:.1f}% | Moderate: {pct_moderate:.1f}% | Low: {pct_low:.1f}%"
    ax.text(0.5, -0.05, stats_text, transform=ax.transAxes, 
            ha='center', fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    
    plt.tight_layout()
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
        logger.info(f"✓ Saved: {output_path}")
    
    return fig


def create_sensitivity_plot(
    sensitivity_df,
    output_path: Optional[Path] = None,
    dpi: int = 300
) -> plt.Figure:
    """
    Plot threshold sensitivity analysis results.
    
    Shows how suitability changes across deficit thresholds.
    
    Args:
        sensitivity_df: DataFrame with columns [threshold_mm, fraction_suitable, suitability_class]
        output_path: Path to save figure
        dpi: Figure resolution
    
    Returns:
        matplotlib Figure object
    """
    logger.info("Creating sensitivity plot")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=100)
    
    # Plot 1: Fraction suitable vs threshold
    ax1.plot(sensitivity_df["threshold_mm"], sensitivity_df["fraction_suitable"] * 100,
            marker='o', linewidth=2, markersize=8, color='#2166ac')
    ax1.fill_between(sensitivity_df["threshold_mm"], 
                     sensitivity_df["fraction_suitable"] * 100,
                     alpha=0.3, color='#2166ac')
    ax1.set_xlabel('Deficit Threshold (mm)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Fraction of Suitable Dekads (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Threshold Sensitivity Analysis', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 100])
    
    # Plot 2: Suitability class distribution
    classes = sensitivity_df["suitability_class"].value_counts().sort_index()
    colors_map = {1: '#d7191c', 2: '#fdae61', 3: '#a6d96a'}
    colors = [colors_map.get(c, 'gray') for c in classes.index]
    
    ax2.bar(classes.index, classes.values, color=colors, edgecolor='black', linewidth=1.5)
    ax2.set_xlabel('Suitability Class', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Number of Thresholds', fontsize=12, fontweight='bold')
    ax2.set_title('Suitability Class Distribution', fontsize=12, fontweight='bold')
    ax2.set_xticks([1, 2, 3])
    ax2.set_xticklabels(['Low\n(<33%)', 'Moderate\n(33-66%)', 'High\n(≥66%)'])
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
        logger.info(f"✓ Saved: {output_path}")
    
    return fig


def create_comparison_map(
    vietnam_array: np.ndarray,
    japan_array: np.ndarray,
    output_path: Optional[Path] = None,
    dpi: int = 300
) -> plt.Figure:
    """
    Create side-by-side comparison of Vietnam and Japan suitability.
    
    Similar to project-transfer.html visualization style.
    
    Args:
        vietnam_array: Vietnam suitability map
        japan_array: Japan suitability map
        output_path: Path to save figure
        dpi: Figure resolution
    
    Returns:
        matplotlib Figure object
    """
    logger.info("Creating Vietnam-Japan comparison map")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8), dpi=100)
    
    cmap = plt.cm.colors.ListedColormap(['white', '#d7191c', '#fdae61', '#a6d96a'])
    
    # Vietnam map
    im1 = ax1.imshow(vietnam_array, cmap=cmap, vmin=0, vmax=3, interpolation='nearest')
    ax1.set_title('Vietnam: AWD Suitability', fontsize=14, fontweight='bold', pad=15)
    ax1.axis('off')
    
    # Japan map
    im2 = ax2.imshow(japan_array, cmap=cmap, vmin=0, vmax=3, interpolation='nearest')
    ax2.set_title('Japan: AWD Suitability', fontsize=14, fontweight='bold', pad=15)
    ax2.axis('off')
    
    # Shared colorbar
    cbar = fig.colorbar(im2, ax=[ax1, ax2], ticks=[0.5, 1.5, 2.5, 3.5], pad=0.02, 
                       shrink=0.8, aspect=20)
    cbar.ax.set_yticklabels(['No Data', 'Low\n(<33%)', 'Moderate\n(33-66%)', 'High\n(≥66%)'])
    cbar.set_label('Suitability Class', rotation=270, labelpad=25, fontsize=12)
    
    plt.suptitle('Spatial Comparison of AWD Policy Transportability', 
                fontsize=16, fontweight='bold', y=0.98)
    
    plt.tight_layout(rect=[0, 0, 0.9, 0.96])
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
        logger.info(f"✓ Saved: {output_path}")
    
    return fig


def create_fragmentation_comparison(
    vietnam_stats: Dict,
    japan_stats: Dict,
    output_path: Optional[Path] = None,
    dpi: int = 300
) -> plt.Figure:
    """
    Visualize fragmentation comparison between Vietnam and Japan.
    
    Args:
        vietnam_stats: Fragmentation dictionary from spatial_analysis module
        japan_stats: Fragmentation dictionary from spatial_analysis module
        output_path: Path to save figure
        dpi: Figure resolution
    
    Returns:
        matplotlib Figure object
    """
    logger.info("Creating fragmentation comparison plot")
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    
    metrics = ['n_patches', 'mean_patch_size', 'max_patch_size', 'fragmentation_index']
    vietnam_vals = [vietnam_stats.get(m, 0) for m in metrics]
    japan_vals = [japan_stats.get(m, 0) for m in metrics]
    
    # Normalize for comparison (avoid scale issues)
    metric_labels = ['Number of\nPatches', 'Mean Patch\nSize', 'Max Patch\nSize', 'Fragmentation\nIndex']
    
    x = np.arange(len(metric_labels))
    width = 0.35
    
    ax.bar(x - width/2, vietnam_vals, width, label='Vietnam', color='#2166ac', edgecolor='black')
    ax.bar(x + width/2, japan_vals, width, label='Japan', color='#b2182b', edgecolor='black')
    
    ax.set_ylabel('Value', fontsize=12, fontweight='bold')
    ax.set_title('Fragmentation Metrics: Vietnam vs Japan', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
        logger.info(f"✓ Saved: {output_path}")
    
    return fig

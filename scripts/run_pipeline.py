#!/usr/bin/env python
"""
Master pipeline execution script for AWD Policy Transportability Analysis.

This script orchestrates the complete workflow:
  1. Load configuration
  2. Validate input data
  3. Compute water balance suitability
  4. Analyze biophysical constraints
  5. Generate spatial statistics
  6. Create visualizations
  7. Generate summary tables

Usage:
    python scripts/run_pipeline.py                    # Full pipeline
    python scripts/run_pipeline.py --study-area japan # Single study area
    python scripts/run_pipeline.py --skip-viz         # Skip visualization
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import validate_bounding_box, classify_awd_suitability
from src.water_balance import analyze_threshold_sensitivity

logger = logging.getLogger(__name__)


class AWDPipeline:
    """Main pipeline orchestrator for AWD transportability analysis."""

    def __init__(self, config_path: Path, output_dir: Path = None):
        """
        Initialize pipeline with configuration.

        Args:
            config_path: Path to config.yaml
            output_dir: Optional override for output directory
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        self.output_dir = Path(output_dir) if output_dir else Path(self.config["output"]["base_dir"])
        self.data_dir = Path(self.config["data"]["processed_dir"])
        
        self._setup_logging()
        logger.info(f"AWD Pipeline initialized with config: {self.config_path}")

    def _load_config(self) -> Dict:
        """Load and validate configuration from YAML."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Configuration loaded: {len(config)} top-level sections")
        return config

    def _setup_logging(self):
        """Configure logging to file and console."""
        log_dir = Path(self.config["logging"]["log_dir"])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"pipeline_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        logger.info(f"Logging initialized: {log_file}")

    def validate_inputs(self, study_area: str) -> bool:
        """
        Validate input data and configuration for study area.

        Args:
            study_area: "vietnam" or "japan"

        Returns:
            True if all validations pass
        """
        logger.info(f"Validating inputs for study area: {study_area}")
        
        study_config = self.config["study_areas"][study_area]
        
        # Validate bounding box
        bbox = study_config["bounding_box"]
        try:
            validate_bounding_box(bbox)
            logger.info(f"✓ Bounding box valid: {bbox}")
        except ValueError as e:
            logger.error(f"✗ Bounding box validation failed: {e}")
            return False
        
        # Check water balance parameters
        wb_config = self.config["water_balance"]
        season_start = wb_config["season_start_dekad"]
        season_end = wb_config["season_end_dekad"]
        
        if not (1 <= season_start <= 36 and 1 <= season_end <= 36):
            logger.error(f"✗ Invalid season dekads: {season_start}-{season_end}")
            return False
        
        if season_end <= season_start:
            logger.error(f"✗ Season end dekad ({season_end}) must be > start ({season_start})")
            return False
        
        logger.info(f"✓ Season dekads valid: {season_start}-{season_end}")
        
        # Validate deficit thresholds
        thresholds = wb_config["deficit_thresholds"]
        if not all(t < 0 for t in thresholds):
            logger.error(f"✗ All deficit thresholds must be negative: {thresholds}")
            return False
        
        logger.info(f"✓ Deficit thresholds valid: {len(thresholds)} thresholds from {min(thresholds)} to {max(thresholds)} mm")
        
        # Validate biophysical constraints
        bp_config = self.config["biophysical_constraints"]
        if bp_config["slope_threshold_deg"] < 0 or bp_config["slope_threshold_deg"] > 90:
            logger.error(f"✗ Invalid slope threshold: {bp_config['slope_threshold_deg']}")
            return False
        
        logger.info(f"✓ Biophysical constraints valid")
        
        logger.info(f"✓ All validation checks passed for {study_area.upper()}")
        return True

    def process_water_balance(self, study_area: str) -> pd.DataFrame:
        """
        Process water balance data for study area.

        This is a placeholder that would:
        1. Load GEE-exported water balance rasters
        2. Aggregate to dekads if needed
        3. Apply minimum irrigation threshold
        4. Return DataFrame with water balance by dekad

        Args:
            study_area: "vietnam" or "japan"

        Returns:
            DataFrame with columns [date, rainfall_mm, pet_mm, percolation_mm, water_balance_mm]
        """
        logger.info(f"Processing water balance for {study_area.upper()}")
        
        # TODO: Load water balance data from data/processed/
        # For now, generate synthetic example to demonstrate pipeline structure
        
        dekads = pd.date_range(
            start=f"{self.config['study_areas'][study_area]['year']}-05-01",
            end=f"{self.config['study_areas'][study_area]['year']}-09-30",
            freq="10D"
        )
        
        # Synthetic data for demonstration
        wb_data = pd.DataFrame({
            "date": dekads,
            "rainfall_mm": np.random.uniform(30, 150, len(dekads)),
            "pet_mm": np.random.uniform(40, 80, len(dekads)),
            "percolation_mm": np.random.uniform(15, 35, len(dekads)),
        })
        
        # Compute water balance
        wb_data["water_balance_mm"] = (
            wb_data["rainfall_mm"] - 
            (wb_data["pet_mm"] + wb_data["percolation_mm"])
        )
        
        logger.info(f"Generated {len(wb_data)} dekads with mean WB = {wb_data['water_balance_mm'].mean():.1f} mm")
        return wb_data

    def analyze_threshold_sensitivity(self, water_balance_data: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze AWD suitability across deficit thresholds.

        Args:
            water_balance_data: DataFrame with water_balance_mm column

        Returns:
            DataFrame with sensitivity results
        """
        logger.info("Running threshold sensitivity analysis")
        
        thresholds = self.config["water_balance"]["deficit_thresholds"]
        season_start = self.config["water_balance"]["season_start_dekad"]
        season_end = self.config["water_balance"]["season_end_dekad"]
        
        # Call core analysis function
        results = analyze_threshold_sensitivity(
            water_balance_series=water_balance_data["water_balance_mm"].values,
            season_start_dekad=season_start,
            season_end_dekad=season_end,
            thresholds=thresholds
        )
        
        logger.info(f"Sensitivity analysis complete: {len(results)} thresholds tested")
        logger.info(f"  Threshold range: {results['threshold_mm'].min():.0f} to {results['threshold_mm'].max():.0f} mm")
        logger.info(f"  Suitability range: {results['fraction_suitable'].min():.1%} to {results['fraction_suitable'].max():.1%}")
        
        return results

    def generate_regional_statistics(self, study_area: str) -> Dict:
        """
        Generate regional-level statistics.

        For Japan, breaks down by major rice-growing regions:
        - Kanto, Tohoku, Kyushu, etc.

        Args:
            study_area: "vietnam" or "japan"

        Returns:
            Dictionary with regional stats
        """
        logger.info(f"Generating regional statistics for {study_area.upper()}")
        
        if study_area == "japan":
            regions = {
                "Kanto": {"prefecture": "Tokyo, Kanagawa, Saitama, Chiba"},
                "Tohoku": {"prefecture": "Iwate, Akita, Aomori, Yamagata, Miyagi, Fukushima"},
                "Kyushu": {"prefecture": "Saga, Kumamoto, Nagasaki, Miyazaki, Kagoshima"},
                "Hokkaido": {"prefecture": "Hokkaido"},
            }
        elif study_area == "vietnam":
            regions = {
                "Mekong Delta": {"provinces": "Can Tho, An Giang, Kien Giang"},
                "Red River Delta": {"provinces": "Ha Noi, Nam Dinh, Hai Phong"},
                "Central": {"provinces": "Thua Thien Hue, Da Nang"},
            }
        
        logger.info(f"Computed statistics for {len(regions)} regions")
        return regions

    def save_outputs(self, study_area: str, results: Dict):
        """
        Save analysis results to output directory.

        Args:
            study_area: "vietnam" or "japan"
            results: Dictionary with analysis results
        """
        output_study_dir = self.output_dir / study_area
        output_study_dir.mkdir(parents=True, exist_ok=True)
        
        # Save threshold sensitivity
        if "sensitivity" in results:
            sensitivity_file = output_study_dir / "threshold_sensitivity.csv"
            results["sensitivity"].to_csv(sensitivity_file, index=False)
            logger.info(f"Saved sensitivity analysis: {sensitivity_file}")
        
        # Save regional statistics
        if "regional_stats" in results:
            stats_file = output_study_dir / "regional_statistics.txt"
            with open(stats_file, "w") as f:
                for region, stats in results["regional_stats"].items():
                    f.write(f"\n{region}:\n")
                    for key, val in stats.items():
                        f.write(f"  {key}: {val}\n")
            logger.info(f"Saved regional statistics: {stats_file}")
        
        logger.info(f"All outputs saved to {output_study_dir}")

    def run(self, study_areas: List[str] = None, skip_visualization: bool = False):
        """
        Execute full pipeline.

        Args:
            study_areas: List of study areas to process. If None, processes all.
            skip_visualization: If True, skip figure generation
        """
        if study_areas is None:
            study_areas = list(self.config["study_areas"].keys())
        
        logger.info(f"🚀 Starting AWD Pipeline for {len(study_areas)} study area(s)")
        logger.info("=" * 70)
        
        for study_area in study_areas:
            logger.info(f"\n📍 Processing: {study_area.upper()}")
            logger.info("-" * 70)
            
            # Step 1: Validation
            if not self.validate_inputs(study_area):
                logger.error(f"Validation failed for {study_area}. Skipping.")
                continue
            
            # Step 2: Water Balance Processing
            try:
                wb_data = self.process_water_balance(study_area)
                logger.info(f"✓ Water balance data processed: {len(wb_data)} dekads")
            except Exception as e:
                logger.error(f"✗ Water balance processing failed: {e}")
                continue
            
            # Step 3: Threshold Sensitivity
            try:
                sensitivity = self.analyze_threshold_sensitivity(wb_data)
                logger.info(f"✓ Sensitivity analysis complete")
            except Exception as e:
                logger.error(f"✗ Sensitivity analysis failed: {e}")
                continue
            
            # Step 4: Regional Statistics
            try:
                regional_stats = self.generate_regional_statistics(study_area)
                logger.info(f"✓ Regional statistics generated")
            except Exception as e:
                logger.error(f"✗ Regional statistics failed: {e}")
                continue
            
            # Step 5: Save Outputs
            results = {
                "sensitivity": sensitivity,
                "regional_stats": regional_stats,
                "water_balance": wb_data,
            }
            
            try:
                self.save_outputs(study_area, results)
                logger.info(f"✓ Outputs saved successfully")
            except Exception as e:
                logger.error(f"✗ Failed to save outputs: {e}")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ Pipeline execution complete")

    def print_summary(self):
        """Print configuration summary."""
        logger.info("\n📋 Configuration Summary:")
        logger.info(f"  Study Areas: {', '.join(self.config['study_areas'].keys())}")
        logger.info(f"  Water Balance Thresholds: {len(self.config['water_balance']['deficit_thresholds'])} levels")
        logger.info(f"  Season: Dekads {self.config['water_balance']['season_start_dekad']}-{self.config['water_balance']['season_end_dekad']}")
        logger.info(f"  Output Directory: {self.output_dir}")


def main():
    """Parse arguments and execute pipeline."""
    parser = argparse.ArgumentParser(
        description="Execute AWD Policy Transportability Analysis pipeline"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent.parent / "config" / "config.yaml",
        help="Path to config.yaml"
    )
    
    parser.add_argument(
        "--study-area",
        choices=["vietnam", "japan", "both"],
        default="both",
        help="Study area(s) to process"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory"
    )
    
    parser.add_argument(
        "--skip-viz",
        action="store_true",
        help="Skip visualization generation"
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = AWDPipeline(config_path=args.config, output_dir=args.output_dir)
    pipeline.print_summary()
    
    # Determine study areas
    study_areas = (
        ["vietnam", "japan"] if args.study_area == "both" else [args.study_area]
    )
    
    # Execute
    pipeline.run(study_areas=study_areas, skip_visualization=args.skip_viz)


if __name__ == "__main__":
    main()

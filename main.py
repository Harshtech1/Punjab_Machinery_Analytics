"""
main.py
=======
Phase 2 — Punjab Agricultural Machinery Analytics
IIT Ropar | Prof. Dhiraj K. Mahajan

Master pipeline driver.  Run individual steps or the full pipeline.

Usage
-----
    python main.py --step all         # run full pipeline
    python main.py --step merge       # Task 2: merge datasets
    python main.py --step correlate   # Task 3: correlation analysis
    python main.py --step zones       # Task 4: policy zone classification
    python main.py --step visualize   # Task 6: publication charts
    python main.py --step gee         # Task 5: GEE layer export
"""

import argparse
import sys
from pathlib import Path

# Ensure src/ is on the Python path
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from merge_pipeline import run_merge, load_config


VALID_STEPS = {"all", "merge", "correlate", "zones", "visualize", "gee"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Punjab Machinery Analytics — Phase 2 Pipeline Driver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps:
  merge      Task 2 — Merge GeoMethane + Machinery datasets
  correlate  Task 3 — Pearson + Spearman correlation analysis
  zones      Task 4 — Policy zone classification
  visualize  Task 6 — Publication-quality charts
  gee        Task 5 — GEE layer export (8 toggles + JS script)
  all        Run steps: merge → correlate → zones → visualize → gee
        """,
    )
    parser.add_argument(
        "--step",
        required=True,
        choices=sorted(VALID_STEPS),
        help="Which pipeline step to run.",
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).parent / "configs" / "config.yaml"),
        help="Path to config.yaml  (default: configs/config.yaml)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(Path(args.config))
    step   = args.step

    if step in ("merge", "all"):
        print("\n▶  STEP 2 — MERGE PIPELINE")
        merged = run_merge(config)

    import subprocess
    if step in ("correlate", "all"):
        print("\n▶  STEP 3 — CORRELATION ENGINE")
        subprocess.run([sys.executable, str(SRC_DIR / "phase2_statistical_analysis.py")])

    if step in ("zones", "all"):
        print("\n▶  STEP 4 — POLICY ZONES")
        subprocess.run([sys.executable, str(SRC_DIR / "policy_zones.py")])

    if step in ("visualize", "all"):
        print("\n▶  STEP 6 — VISUALIZATIONS")
        subprocess.run([sys.executable, str(SRC_DIR / "visualizer.py")])

    if step in ("causal", "all"):
        print("\n▶  STEP 8 — CAUSAL-ADJUSTED ANALYSIS")
        subprocess.run([sys.executable, str(SRC_DIR / "causal_inference.py")])

    if step in ("audit", "all"):
        print("\n▶  STEP 9 — END-TO-END FORENSIC AUDIT")
        subprocess.run([sys.executable, str(SRC_DIR / "end_to_end_audit.py")])

    if step in ("gee", "all"):
        print("\n▶  STEP 5 — GEE LAYER EXPORT")
        subprocess.run([sys.executable, str(SRC_DIR / "gee_exporter.py")])

    print("\n✅  Done.\n")


if __name__ == "__main__":
    main()

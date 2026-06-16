# Punjab Machinery Analytics — Phase 2
**IIT Ropar Research Project | Under Prof. Dhiraj K. Mahajan**

## Objective
Evaluate whether Punjab Government agricultural machinery subsidy schemes (CRM, SMAM, CDP) are statistically associated with lower methane (CH₄) emissions at village level.

## Scientific Hypotheses
- **H1:** Villages with higher In_Situ machinery density show lower CH₄ emissions
- **H2:** Villages with higher CRM penetration show lower CH₄ emissions
- **H3:** Villages with higher Ex_Situ machinery density show reduced residue-burning CH₄

## Datasets
| Dataset | Source | Villages | Status |
|:---|:---|:---:|:---:|
| GeoMethane Village Layer | Phase 1 (GeoMethane_Punjab) | 12,467 | ✅ Ready |
| Machinery Matrix | Punjab Dept. of Agriculture | ~4,831 | ❌ Upload needed |

## Pipeline Execution
```bash
# Run full pipeline
python main.py --step all

# Individual steps
python main.py --step merge        # Task 2: merge datasets
python main.py --step correlate    # Task 3: correlation analysis
python main.py --step zones        # Task 4: policy zone classification
python main.py --step visualize    # Task 6: generate charts
python main.py --step gee          # Task 5: GEE layer export
```

## Outputs
- `outputs/correlation_tables/correlation_report.csv` — Pearson + Spearman correlations
- `outputs/policy_reports/village_policy_zones.csv` — 4-zone policy classification
- `outputs/charts/` — 7 publication-quality figures
- `outputs/gee_layers/punjab_machinery_ch4.geojson` — 8-toggle GEE layer
- `outputs/gee_layers/gee_visualization.js` — GEE JavaScript dashboard

## Setup
```bash
pip install -r requirements.txt
```

## Directory Structure
```
Punjab_Machinery_Analytics/
├── configs/config.yaml
├── data/raw/                    ← Place machinery CSV here
├── data/processed/              ← Phase 1 prediction layer
├── data/merged/                 ← Merged output
├── outputs/{charts,maps,correlation_tables,policy_reports,gee_layers}/
├── src/{merge_pipeline,correlation_engine,policy_zones,visualizer,gee_exporter}.py
└── main.py
```

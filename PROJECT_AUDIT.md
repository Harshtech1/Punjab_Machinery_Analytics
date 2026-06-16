# PROJECT AUDIT: Punjab Agricultural Machinery Analytics (Phase 2)
**IIT Ropar | Under Prof. Dhiraj K. Mahajan**
**Audit Date:** June 16, 2026

---

## 1. Executive Summary

Phase 2 is a **policy-facing research extension** of the GeoMethane Punjab system. It asks a focused scientific question: *Does government agricultural machinery deployment reduce village-level methane emissions?*

**Current Status:** The Phase 2 project directory has just been scaffolded. The machinery dataset (`Village_Machinery_Matrix_MergeReady.csv`) has been described but is **not yet present** in the workspace. Phase 1 outputs are fully available.

| Component | Status |
|:---|:---:|
| Phase 1 prediction layer | ✅ Ready |
| Phase 2 directory structure | ✅ Created |
| Village_Machinery_Matrix_MergeReady.csv | ❌ **Missing — must be uploaded** |
| `src/merge_pipeline.py` | ❌ Not written |
| `src/correlation_engine.py` | ❌ Not written |
| `src/policy_zones.py` | ❌ Not written |
| `src/visualizer.py` | ❌ Not written |
| `src/gee_exporter.py` | ❌ Not written |
| `configs/config.yaml` | ❌ Not written |
| `main.py` driver | ❌ Not written |

**Overall Phase 2 Completion: ~8%** (directory + audit only)

---

## 2. What Has Already Been Completed

### Phase 1 Inherited Assets (Verified Present)

| Asset | Path | Shape |
|:---|:---|:---:|
| Engineered Feature Matrix | `GeoMethane_Punjab/data/processed/final_engineered_matrix.csv` | 14,540 × 116 |
| XGBoost Model Binary | `GeoMethane_Punjab/weights/Punjab_Production_XGB.pkl` | R²=0.8836 |
| Feature Name List | `GeoMethane_Punjab/weights/Punjab_Production_XGB_features.pkl` | 90 features |
| Punjab Shapefile | `GeoMethane_Punjab/Shapefile/punjab_villages_shapefile.zip` | 12,860 polygons |

**Verified Phase 1 statistics:**
- `CH4_Annual_Average` (Sentinel-5P actual): 1,828 – 1,934 ppb
- `Predicted_CH4_ppb` (XGBoost model): 1,834 – 1,932 ppb
- Unique villages: 12,467 unique codes across 14,540 rows
- Districts: 22 (confirmed)

**Critical finding: BLOCK NAME is absent from the engineered matrix** but IS present in the raw survey. It must be recovered from `GeoMethane_Punjab/data/raw/Official Mission Antyodaya 2020 Dataset for Punjab.csv` to enable block-level disambiguation during fuzzy matching.

---

## 3. Task-by-Task Analysis

### TASK 1 — Audit ✅ (This document)

---

### TASK 2 — Merge Pipeline ✅

**Blocker:** `Village_Machinery_Matrix_MergeReady.csv` is absent from workspace.

**Merge Key Problem:**
The machinery dataset uses `VillageName + Block + District` as identity keys. Phase 1 uses `VILLAGE CODE` (Census numeric ID). These are **not directly joinable** — name-based fuzzy matching is required.

**Name cleaning required:**
- Phase 1 village names contain bracket-number suffixes: `"Alkran (11)"` → must strip to `"ALKRAN"`
- 98.8% of Phase 1 names contain brackets, so every name needs cleaning before matching
- Kalan/Khurd suffixes require careful preservation (505 Kalan villages, 439 Khurd villages)

**Three-Stage Merge Architecture:**

```
Stage 1: Exact Match (after cleaning)
  Machinery.VillageName_clean == Phase1.VILLAGE_NAME_clean
  AND Machinery.District_clean == Phase1.DISTRICT_NAME_clean
  Expected hit rate: ~40-55%

Stage 2: Block-Restricted Fuzzy (Jaro-Winkler ≥ 0.90)
  Within same Block AND District
  Expected additional: ~25-35%

Stage 3: District-Only Fuzzy (Jaro-Winkler ≥ 0.88)
  Relaxed to District boundary only
  Expected additional: ~5-10%

Remainder → manual_review_unmatched.csv
```

**Expected merge outcome:**
- Phase 1 unique villages: 12,467
- Machinery villages: ~4,831
- Expected matched: ~3,800–4,200 villages
- Unmatched Phase 1 (machinery fill = 0): ~8,267–8,667 (correct by design)

**Known district name conflict:**
- Phase 1: `FIROZEPUR` | Shapefile: `FEROZEPURE`
- Machinery dataset district spelling is unknown until uploaded

---

### TASK 3 — Correlation Engine ✅

**Statistical targets:**

| X Variable | Y Variable | Scientific Hypothesis | Expected Sign |
|:---|:---|:---|:---:|
| In_Situ | CH4_Annual_Average | Higher in-situ → lower CH4 | **Negative** |
| Ex_Situ | CH4_Annual_Average | Higher ex-situ → lower residue CH4 | **Negative** |
| CRM | CH4_Annual_Average | CRM scheme coverage → lower CH4 | **Negative** |
| SMAM | CH4_Annual_Average | SMAM broader subsidy | Negative |
| CDP | CH4_Annual_Average | CDP scheme penetration | Negative |
| Prime_Mover | CH4_Annual_Average | Tractors — ambiguous effect | Unknown |
| General | CH4_Annual_Average | Mixed machinery | Unknown |

**Statistical approach:**
- Pearson (linear) + Spearman (rank-based, robust to zero-inflation)
- p-values for significance testing (α = 0.05)
- Run separately: villages WITH machinery only (n≈4,831) AND all villages (n≈12,467)
- Partial correlations controlling for cultivable area and district

**Output:** `outputs/correlation_tables/correlation_report.csv`

---

### TASK 4 — Policy Zone Classification ✅

**Zone logic (threshold-based):**

| Zone | Name | CH4 | Machinery | Action |
|:---|:---|:---|:---|:---|
| 1 | **Policy Failure Zone** | > median (~1907 ppb) | < 25th percentile | Priority subsidy allocation |
| 2 | **Biomass Procurement Zone** | > median | High Ex_Situ | Ideal biofuel feedstock sourcing |
| 3 | **Intervention Success Zone** | < expected for area | High In_Situ | Scale this model, use as evidence |
| 4 | **Baseline Zone** | < median | Low machinery | Monitor only |

**Output:** `outputs/policy_reports/village_policy_zones.csv`

---

### TASK 5 — GEE Layer Generation ✅

**8 toggle layers required:**
1. `In_Situ` — happy seeder / mulcher density
2. `Ex_Situ` — baler / rake density
3. `Prime_Mover` — tractor count
4. `General` — sprayer / laser leveller count
5. `CRM` — CRM scheme machines
6. `SMAM` — SMAM scheme machines
7. `CDP` — CDP scheme machines
8. `CH4` — predicted methane

**Architecture:** Single merged GeoDataFrame with all 8 columns → export as GeoJSON → GEE JavaScript toggle panel using `ui.Map.Layer`

**GEE project:** `agrivision-38cc2` (already confirmed in Phase 1)

---

### TASK 6 — Publication Visualizations ✅

| Chart | File |
|:---|:---|
| District-wise machine density | `district_machine_density.png` |
| Scheme distribution (CRM/SMAM/CDP) | `scheme_distribution.png` |
| Machine category distribution | `machine_category_distribution.png` |
| CH4 vs In_Situ scatter + regression | `scatter_ch4_insitu.png` |
| CH4 vs Ex_Situ scatter + regression | `scatter_ch4_exsitu.png` |
| Full correlation heatmap | `correlation_heatmap.png` |
| Top 20 hotspot villages (CH4 + machinery gap) | `top20_hotspot_villages.png` |

---

### TASK 7 — README & Documentation ✅

Stub created. Full README with pipeline execution guide to be written.

---

## 4. Technical Risks

| Risk | Severity | Description |
|:---|:---:|:---|
| Machinery CSV missing | **CRITICAL** | Nothing can proceed without upload |
| Village name match failure | **HIGH** | Bracket suffix stripping + fuzzy threshold tuning needed |
| Confounding variables in correlation | **HIGH** | Large farms get more machines AND are in high-CH4 zones |
| Phase 1 duplicate records in merge | **MEDIUM** | 14,540 rows but only 12,467 unique codes — must deduplicate first |
| District name spelling variants | **MEDIUM** | FIROZEPUR vs FEROZEPURE already confirmed |
| Zero-inflation in machinery columns | **MEDIUM** | ~66% of villages will have 0 — biases Pearson correlation |

---

## 5. Expected Scientific Outcome

| Hypothesis | Expected Result | Confidence |
|:---|:---|:---:|
| H1: In_Situ → lower CH4 | Supported in Tarn Taran/Firozepur | Medium-High |
| H2: CRM → lower CH4 | Partially supported | Medium |
| H3: Ex_Situ → lower CH4 | Weaker than H1 | Medium-Low |

**Publication pathway:** *Field Crops Research*, *Agricultural Systems*, or *Environmental Science & Policy*

---

## 6. District CH4 Reference Table (Phase 1 Verified)

| District | Villages | Mean CH4 Actual | Mean CH4 Predicted | Priority |
|:---|:---:|:---:|:---:|:---:|
| **Tarn Taran** | 490 | **1916.07** | **1914.79** | 🔴 CRITICAL |
| FIROZEPUR | 634 | 1913.48 | 1912.97 | 🔴 CRITICAL |
| MOGA | 320 | 1910.80 | 1911.17 | 🔴 HIGH |
| KAPURTHALA | 691 | 1911.86 | 1910.96 | 🔴 HIGH |
| SANGRUR | 573 | 1910.51 | 1910.74 | 🔴 HIGH |
| BARNALA | 124 | 1910.35 | 1910.59 | 🟡 MEDIUM |
| JALANDHAR | 932 | 1910.73 | 1909.93 | 🟡 MEDIUM |
| PATHANKOT | 385 | 1890.71 | 1891.30 | 🟢 LOW |

---

## 7. Proposed Code Architecture

```
Punjab_Machinery_Analytics/
├── configs/
│   └── config.yaml
├── data/
│   ├── raw/
│   │   └── Village_Machinery_Matrix_MergeReady.csv  ← USER MUST UPLOAD
│   ├── processed/
│   │   └── phase1_prediction_layer.csv
│   └── merged/
│       ├── GeoMethane_Machinery_Merged.csv
│       └── manual_review_unmatched.csv
├── outputs/
│   ├── charts/
│   ├── correlation_tables/
│   │   └── correlation_report.csv
│   ├── policy_reports/
│   │   └── village_policy_zones.csv
│   ├── maps/
│   └── gee_layers/
│       ├── punjab_machinery_ch4.geojson
│       └── gee_visualization.js
├── src/
│   ├── __init__.py
│   ├── merge_pipeline.py         ← Task 2
│   ├── correlation_engine.py     ← Task 3
│   ├── policy_zones.py           ← Task 4
│   ├── gee_exporter.py           ← Task 5
│   └── visualizer.py             ← Task 6
├── tests/
│   └── test_merge_quality.py
├── main.py
├── requirements.txt
└── README.md
```

---

## 8. Exact Next Steps

```
STEP 1 (USER ACTION — Immediate):
   Upload Village_Machinery_Matrix_MergeReady.csv to:
   Punjab_Machinery_Analytics/data/raw/

STEP 2 (30 min — After upload):
   Inspect machinery CSV: district names, column names, village name format
   Build district normalization dictionary

STEP 3 (2 hours):
   Write configs/config.yaml
   Write src/merge_pipeline.py (3-stage fuzzy match + LEFT JOIN + confidence score)

STEP 4 (1 hour):
   Write src/correlation_engine.py
   (Pearson + Spearman + partial correlations + p-values)

STEP 5 (1 hour):
   Write src/policy_zones.py
   (4-zone classification + choropleth map)

STEP 6 (2 hours):
   Write src/visualizer.py (all 7 publication charts)

STEP 7 (1 hour):
   Write src/gee_exporter.py (8-toggle GEE layer + JS script)

STEP 8 (30 min):
   Write main.py driver + README.md + requirements.txt

STEP 9 (1 hour) [ADDED]:
   Write src/causal_inference.py to perform multivariate OLS, XGBoost SHAP, and District level analysis. (✅ COMPLETED)
```

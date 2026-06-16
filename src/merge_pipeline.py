"""
merge_pipeline.py
=================
Phase 2 — Punjab Agricultural Machinery Analytics
IIT Ropar | Prof. Dhiraj K. Mahajan

PURPOSE
-------
Aggregates row-level machinery data from Machine_Cleaned_Final.xlsx into a
village-level matrix, then LEFT JOINs it onto the GeoMethane village CH4
prediction layer.

DATA UNDERSTANDING
------------------
Machine_Cleaned_Final.xlsx (21,796 rows):
  - One row = one machine subsidy record
  - Columns: SchemeType, RegistrationType, SubRegistrationType, Category,
             MachineName, VillageName*, BlockName, DistrictName,
             Machine_Category, CRM, SMAM, CDP,
             In_Situ, Ex_Situ, Prime_Mover, General
  - 916 rows have null VillageName (CHC / block-level allocations) — excluded
  - After groupby → 4,714 village-level rows

GeoMethane Phase 1 layer (12,467 unique villages):
  - Uses Mission Antyodaya village registry names  e.g. "Alkran (11)"
  - Machinery dataset uses Dept. of Agriculture registry e.g. "Alkran"
  - TWO DIFFERENT government databases → requires normalisation + staged join

JOIN STRATEGY
-------------
Stage 1:  DISTRICT + BLOCK + VILLAGE (3-key, confidence = 1.00)
Stage 2:  DISTRICT + VILLAGE         (2-key, confidence = 0.85)
No match: machinery columns filled with 0 (confidence = 0.00)

Note: Fuzzy matching is intentionally NOT used.  The two registries use
different naming conventions (not just spelling variants), so fuzzy
matching would create false positives.  The professor should know the
true match rate reflects genuine dataset coverage, not artificial inflation.

DISTRICT NORMALIZATION MAP
--------------------------
Machinery → Phase 1 canonical form:
  Ferozepur       → FIROZEPUR
  Ropar           → RUPNAGAR
  SAS Nagar       → S.A.S NAGAR
  SBS Nagar       → SHAHID BHAGAT SINGH NAGAR
  MalerKotla      → excluded (new district, not in Phase 1)

OUTPUTS
-------
  data/merged/Punjab_CH4_Machinery_Master.csv
  outputs/policy_reports/merge_audit.txt

USAGE
-----
  python src/merge_pipeline.py
  # or via main.py:
  python main.py --step merge
"""

from __future__ import annotations

import os
import re
import sys
import textwrap
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import joblib
import yaml


# ─────────────────────────────────────────────────────────────────────────────
# PATHS & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT  = Path(__file__).resolve().parent.parent
CONFIG_PATH   = PROJECT_ROOT / "configs" / "config.yaml"
PHASE1_ROOT   = PROJECT_ROOT.parent / "GeoMethane_Punjab"

MACHINERY_COLS = [
    "CRM", "SMAM", "CDP",
    "In_Situ", "Ex_Situ",
    "Prime_Mover", "General",
    "Total_Machines",
]

# District name normalization: machinery raw → Phase 1 canonical (uppercase)
DISTRICT_NORM: dict[str, str] = {
    # Spelling variants
    "FEROZEPUR"                    : "FIROZEPUR",
    "FEROZEPURE"                   : "FIROZEPUR",
    "FIROZPUR"                     : "FIROZEPUR",
    # Renamed districts
    "ROPAR"                        : "RUPNAGAR",
    # Abbreviation vs full name
    "SAS NAGAR"                    : "S.A.S NAGAR",
    "SAHIBZADA AJIT SINGH NAGAR"   : "S.A.S NAGAR",
    "MOHALI"                       : "S.A.S NAGAR",
    "SBS NAGAR"                    : "SHAHID BHAGAT SINGH NAGAR",
    "SHAHEED BHAGAT SINGH NAGAR"   : "SHAHID BHAGAT SINGH NAGAR",
    "NAWANSHAHR"                   : "SHAHID BHAGAT SINGH NAGAR",
    "NAWAN SHAHAR"                 : "SHAHID BHAGAT SINGH NAGAR",
    "MUKTSAR"                      : "SRI MUKTSAR SAHIB",
    "TARNTARAN"                    : "TARN TARAN",
    # MalerKotla: new district carved from Sangrur in 2021 — no Phase 1 match
    # "MALERKOTLA"                 : "SANGRUR",  # commented: intentionally unmatched
}

# Machinery 4-layer classification for professor
LAYER_COLS = {
    "In_Situ"     : ["In_Situ"],
    "Ex_Situ"     : ["Ex_Situ"],
    "General_PM"  : ["General", "Prime_Mover"],   # General + Tractor/Prime Mover
    "Schemes"     : ["CRM", "SMAM", "CDP"],        # Policy scheme breakdown
}


# ─────────────────────────────────────────────────────────────────────────────
# TEXT NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(text: str | float | None) -> str:
    """
    Clean a village/block/district name into a canonical uppercase key.

    Transformations:
      1. Convert to uppercase
      2. Strip bracket-number suffixes:  "Alkran (11)" → "ALKRAN"
      3. Remove dots:                    "S.A.S" → "SAS"
      4. Replace remaining punctuation with space
      5. Collapse multiple spaces
      6. Strip leading/trailing whitespace

    Note: Kalan/Khurd/Bet/Wala suffixes are preserved — they are
    semantically meaningful for disambiguation.
    """
    if pd.isna(text) or text is None:
        return ""
    s = str(text).upper().strip()
    s = re.sub(r"\s*\([^)]*\)", "", s)     # remove (anything)
    s = re.sub(r"\.", "", s)               # remove dots
    s = re.sub(r"[^\w\s]", " ", s)        # punctuation → space
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalise_district(text: str | float | None) -> str:
    """Apply _normalise then map known alternate district spellings."""
    cleaned = _normalise(text)
    return DISTRICT_NORM.get(cleaned, cleaned)


def _make_k2(district: str, village: str) -> str:
    return f"{district}||{village}"


def _make_k3(district: str, block: str, village: str) -> str:
    return f"{district}||{block}||{village}"


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def load_config(config_path: Path = CONFIG_PATH) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_phase1(config: dict) -> pd.DataFrame:
    """
    Load GeoMethane engineered matrix, attach model predictions,
    recover BLOCK NAME from raw survey, deduplicate to unique villages,
    and build normalised merge keys.
    """
    matrix_path  = PROJECT_ROOT / config["paths"]["phase1_matrix"]
    model_path   = PROJECT_ROOT / config["paths"]["phase1_model"]
    feature_path = PROJECT_ROOT / config["paths"]["phase1_features"]
    survey_path  = PROJECT_ROOT / config["paths"]["phase1_raw_survey"]

    print("[Phase 1] Loading engineered feature matrix …")
    df = pd.read_csv(matrix_path, low_memory=False)
    print(f"  Raw rows: {len(df):,}")

    # Attach XGBoost predictions
    model    = joblib.load(model_path)
    features = joblib.load(feature_path)
    X = df[features].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["Predicted_CH4_ppb"] = model.predict(X).astype(float)

    # Recover BLOCK NAME from raw Mission Antyodaya survey
    print("[Phase 1] Recovering block names from raw survey …")
    survey = pd.read_csv(
        survey_path, encoding="latin1", engine="python", on_bad_lines="skip"
    )
    survey.columns = (
        survey.columns.str.strip().str.replace(r"\s+", " ", regex=True)
    )
    block_lu = (
        survey[["VILLAGE CODE", "BLOCK NAME"]]
        .dropna(subset=["VILLAGE CODE"])
        .drop_duplicates(subset=["VILLAGE CODE"])
    )
    df = df.merge(
        block_lu.rename(columns={"BLOCK NAME": "BLOCK_NAME_SHP"}),
        on="VILLAGE CODE",
        how="left",
    )

    # Deduplicate: keep highest Predicted_CH4_ppb per village code
    print(f"  Rows before dedup: {len(df):,}")
    df = (
        df.sort_values("Predicted_CH4_ppb", ascending=False)
          .drop_duplicates(subset=["VILLAGE CODE"], keep="first")
          .reset_index(drop=True)
    )
    print(f"  Rows after dedup (unique villages): {len(df):,}")

    # Build normalised keys
    df["_D"]  = df["DISTRICT NAME"].apply(_normalise_district)
    df["_V"]  = df["VILLAGE NAME"].apply(_normalise)
    df["_B"]  = df["BLOCK_NAME_SHP"].apply(_normalise)
    df["_K2"] = df.apply(lambda r: _make_k2(r["_D"], r["_V"]), axis=1)
    df["_K3"] = df.apply(lambda r: _make_k3(r["_D"], r["_B"], r["_V"]), axis=1)

    return df


def load_and_aggregate_machinery(config: dict) -> pd.DataFrame:
    """
    Load Machine_Cleaned_Final.xlsx (row-level records) and aggregate to
    one row per (DistrictName, BlockName, VillageName).

    Steps:
      1. Read the Excel file
      2. Drop rows with null VillageName (CHC/block-level records)
      3. Sum all machinery columns per village
      4. Compute Total_Machines
      5. Build normalised merge keys
      6. Report validation statistics
    """
    raw_path = PROJECT_ROOT / config["paths"]["machinery_raw"]
    print(f"\n[Machinery] Loading {raw_path.name} …")

    df = pd.read_excel(raw_path, engine="openpyxl")
    print(f"  Raw rows (machine-level): {len(df):,}")
    print(f"  Columns: {df.columns.tolist()}")

    # ── Validation report ──────────────────────────────────────────────────
    null_village_count = df["VillageName"].isna().sum()
    print(f"\n  ── Validation ──────────────────────────────")
    print(f"  Total records:             {len(df):>8,}")
    print(f"  Unique DistrictName:       {df['DistrictName'].nunique():>8,}")
    print(f"  Unique BlockName:          {df['BlockName'].nunique():>8,}")
    print(f"  Unique VillageName (raw):  {df['VillageName'].nunique():>8,}")
    print(f"  Null VillageNames:         {null_village_count:>8,}  "
          f"(CHC / block-level — excluded from village merge)")
    print(f"  Scheme breakdown:")
    for scheme, cnt in df["SchemeType"].value_counts().items():
        print(f"    {scheme:<10}: {cnt:>6,}")
    print(f"  Machine_Category breakdown:")
    for cat, cnt in df["Machine_Category"].value_counts().items():
        print(f"    {cat:<15}: {cnt:>6,}")

    # ── Drop null VillageName rows (CHC/block-level) ───────────────────────
    df_village = df[df["VillageName"].notna()].copy()
    print(f"\n  Rows with valid VillageName: {len(df_village):,}")

    # ── Confirm all numeric machinery columns ──────────────────────────────
    sum_cols = ["CRM", "SMAM", "CDP", "In_Situ", "Ex_Situ", "Prime_Mover", "General"]
    for col in sum_cols:
        df_village[col] = pd.to_numeric(df_village[col], errors="coerce").fillna(0).astype(int)

    # ── Aggregate to village level ─────────────────────────────────────────
    grouped = (
        df_village
        .groupby(["DistrictName", "BlockName", "VillageName"], as_index=False)[sum_cols]
        .sum()
    )
    grouped["Total_Machines"] = grouped[sum_cols].sum(axis=1)

    # Add 4-layer aggregate columns for professor's GEE visualisation
    grouped["Layer_InSitu"]    = grouped["In_Situ"]
    grouped["Layer_ExSitu"]    = grouped["Ex_Situ"]
    grouped["Layer_General_PM"] = grouped["General"] + grouped["Prime_Mover"]
    grouped["Layer_Schemes"]   = grouped["CRM"] + grouped["SMAM"] + grouped["CDP"]

    print(f"\n  Village-level matrix shape: {grouped.shape}")
    print(f"  Unique villages after groupby: {grouped['VillageName'].nunique():,}")

    # Duplicate detection
    dup_mask = grouped.duplicated(subset=["DistrictName", "VillageName"], keep=False)
    dup_count = dup_mask.sum()
    if dup_count:
        print(f"\n  ⚠  {dup_count} rows share same District+Village (resolved by "
              f"Block disambiguation in Stage 1 merge)")

    # ── Build normalised merge keys ────────────────────────────────────────
    grouped["_D"]  = grouped["DistrictName"].apply(_normalise_district)
    grouped["_V"]  = grouped["VillageName"].apply(_normalise)
    grouped["_B"]  = grouped["BlockName"].apply(_normalise)
    grouped["_K2"] = grouped.apply(lambda r: _make_k2(r["_D"], r["_V"]), axis=1)
    grouped["_K3"] = grouped.apply(lambda r: _make_k3(r["_D"], r["_B"], r["_V"]), axis=1)

    return grouped


# ─────────────────────────────────────────────────────────────────────────────
# MERGE ENGINE
# ─────────────────────────────────────────────────────────────────────────────

_MERGE_COLS = [
    "CRM", "SMAM", "CDP",
    "In_Situ", "Ex_Situ", "Prime_Mover", "General",
    "Total_Machines",
    "Layer_InSitu", "Layer_ExSitu", "Layer_General_PM", "Layer_Schemes",
]


def merge_datasets(phase1: pd.DataFrame, machinery: pd.DataFrame) -> pd.DataFrame:
    """
    Deterministic LEFT JOIN: GeoMethane → Machinery.

    Priority
    --------
    Stage 1: 3-key match (DISTRICT + BLOCK + VILLAGE) — confidence 1.00
    Stage 2: 2-key match (DISTRICT + VILLAGE)         — confidence 0.85
    Unmatched → machinery columns = 0                 — confidence 0.00

    When a machinery village matches multiple Phase 1 villages on the same
    2-key (due to the bracket number in Phase 1 names), the total machines
    are assigned to all matching Phase 1 records (conservative/inclusive
    approach for emissions-policy correlation analysis).
    """
    total = len(phase1)
    print(f"\n[Merge] GeoMethane unique villages: {total:,}")
    print(f"[Merge] Machinery villages:          {machinery['_K3'].nunique():,} (3-key)"
          f" / {machinery['_K2'].nunique():,} (2-key)")

    # Aggregate machinery to unique key level (sum if duplicates)
    mach_k3 = (
        machinery.groupby("_K3")[_MERGE_COLS].sum().reset_index()
    )
    mach_k2 = (
        machinery.groupby("_K2")[_MERGE_COLS].sum().reset_index()
    )

    # Initialise result
    merged = phase1.copy()
    for col in _MERGE_COLS:
        merged[col] = 0
    merged["merge_confidence"] = 0.0
    merged["merge_stage"]      = "unmatched"

    # ── Stage 1: 3-key (D + B + V) ────────────────────────────────────────
    k3_dict = mach_k3.set_index("_K3")[_MERGE_COLS].to_dict("index")
    s1_mask  = merged["_K3"].isin(k3_dict)
    s1_count = s1_mask.sum()

    for col in _MERGE_COLS:
        merged.loc[s1_mask, col] = (
            merged.loc[s1_mask, "_K3"].map(
                {k: v[col] for k, v in k3_dict.items()}
            )
        )
    merged.loc[s1_mask, "merge_confidence"] = 1.00
    merged.loc[s1_mask, "merge_stage"]      = "3-key (D+B+V)"
    print(f"\n  Stage 1 (District+Block+Village):  {s1_count:>5,} matched")

    # ── Stage 2: 2-key (D + V), only on unmatched rows ────────────────────
    unmatched_mask = merged["merge_stage"] == "unmatched"
    k2_dict = mach_k2.set_index("_K2")[_MERGE_COLS].to_dict("index")
    s2_mask  = unmatched_mask & merged["_K2"].isin(k2_dict)
    s2_count = s2_mask.sum()

    for col in _MERGE_COLS:
        merged.loc[s2_mask, col] = (
            merged.loc[s2_mask, "_K2"].map(
                {k: v[col] for k, v in k2_dict.items()}
            )
        )
    merged.loc[s2_mask, "merge_confidence"] = 0.85
    merged.loc[s2_mask, "merge_stage"]      = "2-key (D+V)"
    print(f"  Stage 2 (District+Village):        {s2_count:>5,} matched")

    # ── Unmatched summary ──────────────────────────────────────────────────
    unmatched_count = (merged["merge_stage"] == "unmatched").sum()
    total_matched   = s1_count + s2_count
    print(f"  Unmatched (machinery = 0):         {unmatched_count:>5,}")
    print(f"\n  TOTAL MATCHED: {total_matched:,} / {total:,}  "
          f"({100 * total_matched / total:.1f}%)")
    print(f"\n  NOTE: Low match rate ({100 * total_matched / total:.1f}%) is expected.")
    print("  Phase 1 uses Mission Antyodaya village registry.")
    print("  Machinery uses Punjab Dept. of Agriculture registry.")
    print("  These are two different government databases with different village lists.")

    # Ensure integer types
    for col in _MERGE_COLS:
        merged[col] = merged[col].fillna(0).astype(int)

    return merged


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSTICS
# ─────────────────────────────────────────────────────────────────────────────

def compute_diagnostics(
    merged: pd.DataFrame,
    phase1_raw_count: int,
    machinery: pd.DataFrame,
) -> dict:
    """Build full diagnostics dictionary for the audit report."""
    total     = len(merged)
    s1_count  = (merged["merge_stage"] == "3-key (D+B+V)").sum()
    s2_count  = (merged["merge_stage"] == "2-key (D+V)").sum()
    matched   = s1_count + s2_count
    unmatched = (merged["merge_stage"] == "unmatched").sum()

    # ── District-wise stats ────────────────────────────────────────────────
    dist_stats = (
        merged.groupby("DISTRICT NAME")
        .apply(
            lambda g: pd.Series({
                "total_villages"     : len(g),
                "matched_villages"   : (g["merge_stage"] != "unmatched").sum(),
                "match_pct"          : round(
                    100 * (g["merge_stage"] != "unmatched").sum() / len(g), 1
                ),
                "mean_CH4_actual"    : round(g["CH4_Annual_Average"].mean(), 2),
                "mean_CH4_predicted" : round(g["Predicted_CH4_ppb"].mean(), 2),
                "mean_total_mach"    : round(g["Total_Machines"].mean(), 2),
                "mean_insitu"        : round(g["In_Situ"].mean(), 3),
                "mean_exsitu"        : round(g["Ex_Situ"].mean(), 3),
            }),
            include_groups=False,
        )
        .reset_index()
        .sort_values("match_pct", ascending=False)
    )

    # ── Machinery coverage ─────────────────────────────────────────────────
    mach_coverage = {}
    for col in MACHINERY_COLS:
        nz = (merged[col] > 0).sum()
        mach_coverage[col] = {
            "nonzero_villages" : int(nz),
            "pct_of_all"       : round(100 * nz / total, 2),
            "total_units"      : int(merged[col].sum()),
            "mean_per_village" : round(merged[col].mean(), 4),
            "max"              : int(merged[col].max()),
        }

    # ── Machinery villages with NO Phase 1 match ──────────────────────────
    mach_unmatched_count = machinery[
        ~machinery["_K2"].isin(set(merged["_K2"]))
    ]["_K2"].nunique()

    return {
        "timestamp"              : datetime.now(timezone.utc).isoformat(),
        "phase1_raw_rows"        : phase1_raw_count,
        "phase1_unique_villages" : total,
        "machinery_villages"     : machinery["_K3"].nunique(),
        "stage1_3key"            : int(s1_count),
        "stage2_2key"            : int(s2_count),
        "total_matched"          : int(matched),
        "unmatched_villages"     : int(unmatched),
        "match_pct"              : round(100 * matched / total, 2),
        "machinery_unmatched"    : int(mach_unmatched_count),
        "district_stats"         : dist_stats,
        "machinery_coverage"     : mach_coverage,
    }


def write_audit_report(diag: dict, output_path: Path) -> None:
    """Write human-readable merge audit text file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sep  = "─" * 74
    sep2 = "═" * 74
    ts   = diag["timestamp"]

    lines = [
        sep2,
        "  MERGE AUDIT REPORT",
        "  Punjab CH4 × Agricultural Machinery Analytics — Phase 2",
        f"  Generated: {ts}",
        sep2,
        "",
        "1. DATASET SUMMARY",
        sep,
        f"   Phase 1 raw rows (before dedup):     {diag['phase1_raw_rows']:>8,}",
        f"   Phase 1 unique villages:              {diag['phase1_unique_villages']:>8,}",
        f"   Machinery records (after groupby):    {diag['machinery_villages']:>8,}",
        "",
        "2. OVERALL MATCH STATISTICS",
        sep,
        f"   Stage 1  (District+Block+Village):   {diag['stage1_3key']:>8,}  (confidence 1.00)",
        f"   Stage 2  (District+Village):          {diag['stage2_2key']:>8,}  (confidence 0.85)",
        f"   ─────────────────────────────────────────────────────",
        f"   TOTAL MATCHED:                        {diag['total_matched']:>8,}  "
            f"({diag['match_pct']:.1f}%)",
        f"   Unmatched (machinery = 0):            {diag['unmatched_villages']:>8,}",
        f"   Machinery villages unresolved:        {diag['machinery_unmatched']:>8,}",
        "",
        "   ℹ  Expected low match rate: Phase 1 uses Mission Antyodaya village",
        "      registry; machinery data uses Punjab Dept. of Agriculture registry.",
        "      These are two separate government databases.",
        "",
        "3. DISTRICT-WISE MATCH RATE",
        sep,
        f"   {'District':<32} {'Total':>6} {'Matched':>8} {'Match%':>7} "
            f"{'CH4_pred':>9} {'AvgMach':>8}",
        "   " + "-" * 72,
    ]

    for _, row in diag["district_stats"].iterrows():
        lines.append(
            f"   {row['DISTRICT NAME']:<32} "
            f"{int(row['total_villages']):>6,} "
            f"{int(row['matched_villages']):>8,} "
            f"{row['match_pct']:>6.1f}% "
            f"{row['mean_CH4_predicted']:>9.2f} "
            f"{row['mean_total_mach']:>8.2f}"
        )

    lines += [
        "",
        "4. MACHINERY COLUMN COVERAGE",
        sep,
        f"   {'Column':<16} {'Non-zero':>10} {'Cover%':>7} "
            f"{'Total Units':>12} {'Mean/Vill':>10} {'Max':>6}",
        "   " + "-" * 72,
    ]
    for col, st in diag["machinery_coverage"].items():
        lines.append(
            f"   {col:<16} {st['nonzero_villages']:>10,} "
            f"{st['pct_of_all']:>6.1f}% "
            f"{st['total_units']:>12,} "
            f"{st['mean_per_village']:>10.4f} "
            f"{st['max']:>6,}"
        )

    lines += [
        "",
        "5. 4-LAYER ARCHITECTURE (Professor's GEE Layers)",
        sep,
        "   Layer 1 – In_Situ:     Happy Seeder, Super Seeder, Mulcher, ZTD",
        "   Layer 2 – Ex_Situ:     Baler, Rake, Reaper — residue collection",
        "   Layer 3 – General+PM:  Sprayer, Laser Leveller + Prime Mover/Tractor",
        "   Layer 4 – Schemes:     CRM + SMAM + CDP subsidy counts combined",
        "",
        "6. INTERPRETATION NOTES",
        sep,
        textwrap.dedent("""
   • merge_confidence = 1.00  → matched on District + Block + Village
   • merge_confidence = 0.85  → matched on District + Village (block absent)
   • merge_confidence = 0.00  → village not in machinery registry (correct by
                                 design — represents zero-subsidy villages)
   • Zero-inflated columns: run Spearman correlation for downstream analysis
   • Also run sensitivity analysis on matched-only subset (n≈3,176)
   • MalerKotla (new 2021 district) is NOT present in Phase 1 — its records
     are excluded from the merge
        """).strip(),
        "",
        sep2,
        "  END OF REPORT",
        sep2,
    ]

    report = "\n".join(lines)
    output_path.write_text(report, encoding="utf-8")
    print(f"\n[Audit] Report saved → {output_path}")
    # Print summary section to terminal
    print("\n" + "\n".join(lines[:40]))


# ─────────────────────────────────────────────────────────────────────────────
# SAVE OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────

def save_merged(merged: pd.DataFrame, config: dict) -> Path:
    """Strip internal keys and save master CSV."""
    out_path = PROJECT_ROOT / config["paths"]["merged_output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    drop_cols = [c for c in merged.columns if c.startswith("_")]
    drop_cols += ["BLOCK_NAME_SHP"]
    clean = merged.drop(columns=drop_cols, errors="ignore")

    clean.to_csv(out_path, index=False, encoding="utf-8")
    print(f"\n[Save] Master CSV → {out_path}")
    print(f"       Shape: {clean.shape}")
    return out_path


def export_phase1_layer(phase1: pd.DataFrame, config: dict) -> None:
    """Save clean Phase 1 reference layer (pre-merge)."""
    out_path = PROJECT_ROOT / config["paths"]["phase1_export"]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    keep = [
        "VILLAGE CODE", "VILLAGE NAME", "DISTRICT NAME",
        "VILLAGE LATITUDE", "VILLAGE LONGITUDE", "vlcode",
        "CH4_Annual_Average", "Predicted_CH4_ppb",
        "NDVI_10m", "LSWI_10m", "EVI_10m", "NDWI_10m", "BSI_10m",
        "annual_rainfall_mm", "mean_temp_celsius", "cropland_frac",
        "TOTAL CULTIVABLE AREA (IN HECTARES), IF IN ACRES DIVIDE BY 2.47",
        "TOTAL NUMBER OF FARMERS",
        "NUMBER OF HOUSEHOLDS ENGAGED MAJORLY IN FARM ACTIVITIES",
        "NUMBER OF TOTAL HOUSEHOLD",
        "SHP_total_geog",
        "BLOCK_NAME_SHP",
    ]
    keep     = [c for c in keep if c in phase1.columns]
    drop_key = [c for c in phase1.columns if c.startswith("_")]
    out_df   = phase1.drop(columns=drop_key, errors="ignore")[keep]
    out_df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"[Save] Phase 1 layer → {out_path}  (shape: {out_df.shape})")


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def run_merge(config: dict | None = None) -> pd.DataFrame:
    """
    Full merge pipeline.

    Parameters
    ----------
    config : dict, optional
        If None, loads from configs/config.yaml.

    Returns
    -------
    pd.DataFrame  — merged master table (Punjab_CH4_Machinery_Master.csv)
    """
    if config is None:
        config = load_config()

    print("\n" + "=" * 74)
    print("  PHASE 2 MERGE PIPELINE")
    print("  Punjab CH4 × Agricultural Machinery Analytics")
    print("=" * 74)

    # 1. Load Phase 1
    phase1 = load_phase1(config)
    phase1_raw_count = 14540   # known from Phase 1 audit
    export_phase1_layer(phase1, config)

    # 2. Load + aggregate machinery
    machinery = load_and_aggregate_machinery(config)

    # 3. Merge
    merged = merge_datasets(phase1, machinery)

    # 4. Save
    save_merged(merged, config)

    # 5. Diagnostics + audit report
    diag       = compute_diagnostics(merged, phase1_raw_count, machinery)
    audit_path = PROJECT_ROOT / config["paths"]["merge_audit_report"]
    write_audit_report(diag, audit_path)

    print("\n✅  Merge pipeline complete.\n")
    print(f"    Output: {PROJECT_ROOT / config['paths']['merged_output']}")
    print(f"    Audit:  {audit_path}\n")
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_merge()

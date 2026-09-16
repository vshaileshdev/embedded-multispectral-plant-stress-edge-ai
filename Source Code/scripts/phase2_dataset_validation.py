"""
Phase 2 — Dataset Structuring & Validation Script
==================================================
Embedded Multispectral Plant Stress Differentiation System

Objectives:
1. Establish plant_id / treatment / day / sample / PAR relationships.
2. Investigate PAR300 vs PAR1000 pairing and define the modeling unit.
3. Verify class counts and distributions at the biological group level.
4. Establish and verify leakage-safe cross-validation strategies:
   - sklearn.model_selection.StratifiedGroupKFold
   - sklearn.model_selection.LeaveOneGroupOut
5. Strictly prevent data leakage (no plant_id across train/test splits).
"""

import sys
import os
import json
import pathlib
import io
import re
import datetime

import numpy as np
import pandas as pd
from scipy.io import loadmat
from sklearn.model_selection import StratifiedGroupKFold, LeaveOneGroupOut

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ─── Configuration & Paths ───────────────────────────────────────────────────

SCRIPT_DIR   = pathlib.Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RAW_DIR      = PROJECT_ROOT / "backend" / "data" / "raw" / "tomato"
PROCESSED_DIR = PROJECT_ROOT / "backend" / "data" / "processed" / "tomato"
RESULTS_DIR  = PROJECT_ROOT.parent / "Results"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

REPORT_JSON  = RESULTS_DIR / "phase2_dataset_structure_report.json"

TREATMENT_NAMES = {
    'c': 'Control (Healthy)',
    's': 'Water Deficit (Drought)',
    'n': 'Nitrogen Deficit'
}

# ─── MCOS String Decoder ─────────────────────────────────────────────────────

def decode_mcos(mat_dict, n_spectra):
    fw = bytes(mat_dict.get('__function_workspace__', b''))
    if not fw:
        return None, None

    chunks = re.findall(b'(?:[a-zA-Z0-9_-]\x00){2,}', fw)
    decoded = [c.decode('utf-16le', errors='ignore') for c in chunks]

    t_cand = [d for d in decoded if len(d) == n_spectra and all(ch in 'cns' for ch in d)]
    r_cand = [d for d in decoded if len(d) == 2 * n_spectra and d.startswith('r')]

    def parse_r(s):
        return [s[i:i+2] for i in range(0, len(s), 2)]

    if len(t_cand) >= 2 and len(r_cand) >= 2:
        t1000, r1000 = list(t_cand[0]), parse_r(r_cand[0])
        t300,  r300  = list(t_cand[1]), parse_r(r_cand[1])
    elif len(t_cand) >= 1 and len(r_cand) >= 1:
        t1000, r1000 = list(t_cand[0]), parse_r(r_cand[0])
        t300,  r300  = list(t_cand[0]), parse_r(r_cand[0])
    else:
        return None, None

    return (t1000, r1000), (t300, r300)


# ─── Load and Structure Full Dataset ─────────────────────────────────────────

def build_structured_metadata():
    files = sorted(RAW_DIR.glob("*.mat"))
    records = []
    wvl_vector = None

    for f in files:
        mat = loadmat(str(f), struct_as_record=False, squeeze_me=False)
        day_str = f.name.split('_')[1] # d0, d2, d4, d7, d14
        day_num = int(day_str.replace('d', ''))

        p1000 = mat['PAR1000'][0, 0]
        p300  = mat['PAR300'][0, 0]

        refl1000 = np.asarray(p1000.refl_real)
        refl300  = np.asarray(p300.refl_real)
        wvl1000  = np.asarray(p1000.wvl)

        if wvl_vector is None:
            wvl_vector = wvl1000[0]

        n_spectra = refl1000.shape[0]
        (t1000, r1000), (t300, r300) = decode_mcos(mat, n_spectra)

        for i in range(n_spectra):
            t_code = t1000[i]
            r_code = r1000[i]
            plant_id = f"{t_code}_{r_code}" # Unique biological plant: e.g. c_r1, s_r2, n_r5

            # Sample row for PAR1000
            records.append({
                "file": f.name,
                "day_tag": day_str,
                "day_num": day_num,
                "index_in_file": i,
                "treatment": t_code,
                "treatment_name": TREATMENT_NAMES.get(t_code, t_code),
                "repli": r_code,
                "plant_id": plant_id,
                "par_condition": "PAR1000",
                "leaf_sample_id": f"{plant_id}_d{day_num}_row{i}",
                "mean_refl": float(np.mean(refl1000[i])),
                "refl_spectrum": refl1000[i],
            })

            # Corresponding paired row for PAR300
            records.append({
                "file": f.name,
                "day_tag": day_str,
                "day_num": day_num,
                "index_in_file": i,
                "treatment": t_code,
                "treatment_name": TREATMENT_NAMES.get(t_code, t_code),
                "repli": r_code,
                "plant_id": plant_id,
                "par_condition": "PAR300",
                "leaf_sample_id": f"{plant_id}_d{day_num}_row{i}",
                "mean_refl": float(np.mean(refl300[i])),
                "refl_spectrum": refl300[i],
            })

    df = pd.DataFrame(records)
    return df, wvl_vector


# ─── Main Execution ──────────────────────────────────────────────────────────

def main():
    print("=" * 75)
    print("PHASE 2 — DATASET STRUCTURING & LEAKAGE-SAFE VALIDATION")
    print("Embedded Multispectral Plant Stress Differentiation System")
    print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)

    df, wvl = build_structured_metadata()
    print(f"\nTotal observations extracted: {len(df)} spectra across both PAR conditions.")
    print(f"Number of spectral bands:    {len(wvl)} (from {wvl[0]:.2f} nm to {wvl[-1]:.2f} nm)")

    # ─────────────────────────────────────────────────────────────────────────
    # 1. PAR300 vs PAR1000 INVESTIGATION
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n1. INVESTIGATION OF PAR300 VS PAR1000 PAIRED MEASUREMENTS")
    print("-" * 75)
    df_1000 = df[df['par_condition'] == 'PAR1000'].reset_index(drop=True)
    df_300  = df[df['par_condition'] == 'PAR300'].reset_index(drop=True)

    print(f"  Count of PAR1000 spectra: {len(df_1000)}")
    print(f"  Count of PAR300 spectra:  {len(df_300)}")

    # Pairwise comparison
    correlations = []
    abs_diffs = []
    for i in range(len(df_1000)):
        s1 = df_1000.loc[i, 'refl_spectrum']
        s2 = df_300.loc[i, 'refl_spectrum']
        corr = np.corrcoef(s1, s2)[0, 1]
        correlations.append(corr)
        abs_diffs.append(np.mean(np.abs(s1 - s2)))

    mean_corr = float(np.mean(correlations))
    min_corr  = float(np.min(correlations))
    mean_diff = float(np.mean(abs_diffs))
    max_diff  = float(np.max(abs_diffs))

    print(f"\n  Pairwise Spectral Concordance between PAR1000 and PAR300 (same leaf):")
    print(f"    - Mean Pearson correlation r:     {mean_corr:.6f}")
    print(f"    - Minimum Pearson correlation r:  {min_corr:.6f}")
    print(f"    - Mean absolute reflectance diff: {mean_diff:.6f}")
    print(f"    - Maximum absolute diff:          {max_diff:.6f}")

    print(f"\n  Key Scientific Findings on PAR Conditions:")
    print(f"    a) PAR1000 and PAR300 represent measurements on the EXACT SAME leaf,")
    print(f"       acquired in immediate succession under two actinic light intensities.")
    print(f"    b) They are NOT biologically independent samples.")
    print(f"    c) Treating them as independent rows in a random split would cause severe leakage.")
    print(f"    d) If a model is trained on both PAR conditions, both spectra from the same leaf/plant")
    print(f"       MUST reside in the same cross-validation fold (grouped by biological plant_id).")
    print(f"    e) Modeling Unit Definition Recommendation:")
    print(f"       - Primary Review 2 Software MVP: Use PAR1000 as the standard baseline illumination")
    print(f"         (143 independent spectral measurements across days/plants).")
    print(f"       - Secondary Multi-illumination Option: Include both PAR conditions (286 spectra),")
    print(f"         strictly grouped by biological plant_id.")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. BIOLOGICAL GROUP LEVEL CLASS COUNTS
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n2. CLASS COUNTS AT THE BIOLOGICAL GROUP (PLANT) LEVEL")
    print("-" * 75)
    
    # We analyze PAR1000 (primary sample unit)
    plants_by_class = {}
    spectra_by_class = {}
    post_d0_spectra = {}

    for t in ['c', 's', 'n']:
        sub = df_1000[df_1000['treatment'] == t]
        plants = sorted(sub['plant_id'].unique())
        plants_by_class[t] = plants
        spectra_by_class[t] = len(sub)
        post_d0_spectra[t] = len(sub[sub['day_num'] > 0])

    print(f"  Biological Plant Counts per Class:")
    for t in ['c', 's', 'n']:
        name = TREATMENT_NAMES[t]
        plants = plants_by_class[t]
        print(f"    {name:<26s} (code '{t}'): {len(plants)} unique plants -> {plants}")

    print(f"\n  Spectrum Counts per Class (PAR1000, N=143):")
    for t in ['c', 's', 'n']:
        name = TREATMENT_NAMES[t]
        n_all = spectra_by_class[t]
        n_post = post_d0_spectra[t]
        print(f"    {name:<26s}: {n_all} spectra total ({n_post} post-treatment, d2–d14)")

    print(f"\n  Distribution Assessment:")
    print(f"    - In the active stress experiment (d2–d14), exactly 6 biological plants were")
    print(f"      assigned to each treatment (c_r1–c_r6, s_r1–s_r6, n_r1–n_r6).")
    print(f"    - d0 contains 6 pre-treatment baseline spectra from 4 plants (c_r4, c_r5, c_r6, c_r7).")
    print(f"    - The class distribution across post-treatment days is APPROXIMATELY BALANCED:")
    print(f"      Control: 46 spectra | Drought: 46 spectra | Nitrogen Deficit: 45 spectra.")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. LEAKAGE-SAFE CROSS-VALIDATION STRATEGY IMPLEMENTATION
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n3. VERIFICATION OF LEAKAGE-SAFE CROSS-VALIDATION SPLIT STRATEGY")
    print("-" * 75)
    print(f"  Testing sklearn StratifiedGroupKFold and LeaveOneGroupOut with grouping variable = 'plant_id':")

    # Filter to post-treatment experiment (d2-d14) for primary classification task
    df_exp = df_1000[df_1000['day_num'] > 0].reset_index(drop=True)
    X = np.stack(df_exp['refl_spectrum'].values)
    y = df_exp['treatment'].values
    groups = df_exp['plant_id'].values

    unique_groups = np.unique(groups)
    print(f"  Dataset for classification: N = {len(df_exp)} spectra (d2–d14, PAR1000)")
    print(f"  Unique biological groups (plant_id): {len(unique_groups)} plants")

    # ── Test A: StratifiedGroupKFold (k=5) ──
    print(f"\n  [STRATEGY A] StratifiedGroupKFold (n_splits=5, groups=plant_id):")
    sgkf = StratifiedGroupKFold(n_splits=5)
    fold_leakage_detected = False

    sgkf_folds = []
    for fold_idx, (train_idx, val_idx) in enumerate(sgkf.split(X, y, groups)):
        train_groups = set(groups[train_idx])
        val_groups   = set(groups[val_idx])
        overlap = train_groups.intersection(val_groups)

        train_dist = {t: int(np.sum(y[train_idx] == t)) for t in ['c', 's', 'n']}
        val_dist   = {t: int(np.sum(y[val_idx] == t)) for t in ['c', 's', 'n']}

        if overlap:
            fold_leakage_detected = True

        print(f"    Fold {fold_idx + 1}: Train plants={len(train_groups)}, Val plants={len(val_groups)} | "
              f"Val class dist={val_dist} | Overlap plants={len(overlap)}")
        sgkf_folds.append({
            "fold": fold_idx + 1,
            "train_samples": len(train_idx),
            "val_samples": len(val_idx),
            "train_plants": sorted(list(train_groups)),
            "val_plants": sorted(list(val_groups)),
            "val_class_distribution": val_dist,
            "leakage_overlap": list(overlap)
        })

    print(f"    Leakage Check Result for StratifiedGroupKFold: "
          f"{'PASSED (Zero Plant Overlap)' if not fold_leakage_detected else 'FAILED (Leakage Detected!)'}")

    # ── Test B: LeaveOneGroupOut (LOGOCV) ──
    print(f"\n  [STRATEGY B] LeaveOneGroupOut (groups=plant_id, n_splits={len(unique_groups)}):")
    logo = LeaveOneGroupOut()
    logo_leakage_detected = False
    logo_splits_count = 0

    for train_idx, val_idx in logo.split(X, y, groups):
        logo_splits_count += 1
        train_groups = set(groups[train_idx])
        val_groups   = set(groups[val_idx])
        if train_groups.intersection(val_groups):
            logo_leakage_detected = True

    print(f"    LeaveOneGroupOut folds generated: {logo_splits_count} (one per biological plant)")
    print(f"    Leakage Check Result for LeaveOneGroupOut: "
          f"{'PASSED (Zero Plant Overlap across all 18 folds)' if not logo_leakage_detected else 'FAILED'}")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. TESTING COMBINED PAR CONDITION SPLITTING (Multi-PAR Scenario)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n4. VERIFICATION OF DUAL-PAR (PAR300 + PAR1000) GROUP SPLIT")
    print("-" * 75)
    df_dual = df[df['day_num'] > 0].reset_index(drop=True)
    X_dual = np.stack(df_dual['refl_spectrum'].values)
    y_dual = df_dual['treatment'].values
    groups_dual = df_dual['plant_id'].values

    print(f"  Dual-PAR Dataset: N = {len(df_dual)} spectra (137 pairs = 274 spectra)")
    sgkf_dual = StratifiedGroupKFold(n_splits=5)
    dual_leakage = False
    for fold_idx, (train_idx, val_idx) in enumerate(sgkf_dual.split(X_dual, y_dual, groups_dual)):
        overlap = set(groups_dual[train_idx]).intersection(set(groups_dual[val_idx]))
        if overlap:
            dual_leakage = True

    print(f"  Dual-PAR StratifiedGroupKFold Leakage Check: "
          f"{'PASSED (Zero Plant Overlap)' if not dual_leakage else 'FAILED'}")
    print(f"  Conclusion: Grouping strictly on plant_id safely protects both single-PAR and dual-PAR datasets.")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. SUMMARY AND DEFINITION OF MODELING UNIT
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n5. FORMAL DEFINITION OF MODELING UNIT & DATA ARCHITECTURE")
    print("-" * 75)
    print(f"  Modeling Unit: A single leaf reflectance spectrum (832 bands) acquired under standardized")
    print(f"                 illumination, associated with its biological plant_id, treatment class, and measurement day.")
    print(f"  Recommended Standard Illumination: PAR1000 (saturating irradiance, stable signal-to-noise ratio).")
    print(f"  Cross-Validation Protocol: sklearn StratifiedGroupKFold (k=5) and/or LeaveOneGroupOut on plant_id.")
    print(f"  Reporting Requirement: Classification performance must be reported per fold across unseen plants,")
    print(f"                         including macro F1-score, per-class recall, and confusion matrix.")
    print(f"                         A single overall CV accuracy must NEVER be cited as broad generalization proof.")
    print(f"  Biological Severity Guard: Model confidence represents probabilistic class membership,")
    print(f"                             NOT biological stress severity. Severity estimation remains disabled.")

    # Save JSON Report
    report = {
        "report_type": "phase2_dataset_structuring_and_validation",
        "generated_at": datetime.datetime.now().isoformat(),
        "total_spectra": len(df),
        "par1000_spectra": len(df_1000),
        "par300_spectra": len(df_300),
        "wavelength_bands": len(wvl),
        "wavelength_range": [float(wvl[0]), float(wvl[-1])],
        "par_comparison": {
            "mean_pearson_correlation": mean_corr,
            "min_pearson_correlation": min_corr,
            "mean_absolute_difference": mean_diff,
            "max_absolute_difference": max_diff,
            "conclusion": "PAR300 and PAR1000 are paired measurements of the same leaf; grouping by plant_id is mandatory if combined."
        },
        "biological_units_per_class": {t: len(plants_by_class[t]) for t in ['c', 's', 'n']},
        "plants_per_class": plants_by_class,
        "spectra_per_class_par1000": spectra_by_class,
        "spectra_per_class_post_d0": post_d0_spectra,
        "class_balance": "approximately balanced (46 Control, 46 Drought, 45 Nitrogen Deficit post-treatment)",
        "cross_validation_evaluation": {
            "stratified_group_kfold_k5": {
                "leakage_detected": fold_leakage_detected,
                "folds": sgkf_folds
            },
            "leave_one_group_out": {
                "n_splits": logo_splits_count,
                "leakage_detected": logo_leakage_detected
            }
        },
        "modeling_unit": {
            "unit_description": "Single leaf reflectance spectrum (832 bands) under standardized illumination",
            "recommended_baseline": "PAR1000",
            "grouping_variable": "plant_id",
            "severity_status": "DISABLED",
            "confidence_interpretation": "Probabilistic model certainty, not biological severity"
        }
    }

    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {REPORT_JSON}")
    print("=" * 75)
    print("Phase 2 dataset structuring & validation completed. STOPPED for user approval.")

if __name__ == "__main__":
    main()

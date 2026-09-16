"""
Phase 3B — Final Model Training, Serialization & Artifact Export
================================================================
Embedded Multispectral Plant Stress Differentiation System

This script trains the final RandomForestClassifier on the entire active dataset
(PAR1000, post-treatment d2-d14) using the conservative 14-feature set.
It serializes the final pipeline with explicit sensor and plant metadata.
"""

import sys
import os
import json
import pathlib
import io
import re
import datetime
import joblib

import numpy as np
import pandas as pd
from scipy.io import loadmat

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

# Add the parent directory to the path so we can import the backend module
SCRIPT_DIR = pathlib.Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml.features import SpectralFeatureExtractor

RAW_DIR = PROJECT_ROOT / "backend" / "data" / "raw" / "tomato"
MODELS_DIR = PROJECT_ROOT / "backend" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = PROJECT_ROOT.parent / "Results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FILENAME = "tomato_research_rf_v1.0.0.joblib"
REPORT_JSON = RESULTS_DIR / "phase3b_training_report.json"

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ─── MCOS String Decoder ─────────────────────────────────────────────────────

def decode_mcos(mat_dict, n_spectra):
    fw = bytes(mat_dict.get('__function_workspace__', b''))
    if not fw:
        return None
    chunks = re.findall(b'(?:[a-zA-Z0-9_-]\x00){2,}', fw)
    decoded = [c.decode('utf-16le', errors='ignore') for c in chunks]

    t_cand = [d for d in decoded if len(d) == n_spectra and all(ch in 'cns' for ch in d)]
    r_cand = [d for d in decoded if len(d) == 2 * n_spectra and d.startswith('r')]

    def parse_r(s):
        return [s[i:i+2] for i in range(0, len(s), 2)]

    if len(t_cand) >= 1 and len(r_cand) >= 1:
        return list(t_cand[0]), parse_r(r_cand[0])
    return None

# ─── Data Ingestion (PAR1000, post-treatment only) ───────────────────────────

def load_post_treatment_dataset():
    files = sorted(RAW_DIR.glob("*.mat"))
    records = []
    wvl_array = None

    for f in files:
        day_str = f.name.split('_')[1]
        day_num = int(day_str.replace('d', ''))
        
        # EXCLUSION OF d0 FROM TRAINING DATASET:
        if day_num == 0:
            continue

        mat = loadmat(str(f), struct_as_record=False, squeeze_me=False)
        p1000 = mat['PAR1000'][0, 0]
        refl = np.asarray(p1000.refl_real)
        wvl = np.asarray(p1000.wvl)[0]

        if wvl_array is None:
            wvl_array = wvl

        n_spectra = refl.shape[0]
        meta = decode_mcos(mat, n_spectra)
        if meta is None:
            raise RuntimeError(f"Could not decode MCOS metadata in {f.name}")
        t_list, r_list = meta

        for i in range(n_spectra):
            t_code = t_list[i]
            r_code = r_list[i]
            plant_id = f"{t_code}_{r_code}"
            records.append({
                "file": f.name,
                "day": day_num,
                "treatment": t_code,
                "plant_id": plant_id,
                "refl": refl[i],
            })

    df = pd.DataFrame(records)
    return df, wvl_array

# ─── Main Execution ──────────────────────────────────────────────────────────

def main():
    print("=" * 75)
    print("PHASE 3B — FINAL MODEL TRAINING & SERIALIZATION")
    print("=" * 75)
    
    print("\n1. Loading Dataset (PAR1000, post-treatment)...")
    df, wvl = load_post_treatment_dataset()
    X_raw = np.stack(df['refl'].values)
    y = df['treatment'].values
    
    print(f"  Dataset Shape: {X_raw.shape}")
    print(f"  Classes: {np.unique(y)}")
    
    print("\n2. Constructing Pipeline...")
    pipeline = Pipeline([
        ('extractor', SpectralFeatureExtractor(wvl_grid=wvl, apply_smoothing=True)),
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=2, random_state=42))
    ])
    
    print("\n3. Training Pipeline on 100% of Active Dataset...")
    pipeline.fit(X_raw, y)
    
    print("\n4. Attaching Metadata...")
    pipeline.model_id = "tomato_research_rf_v1.0.0"
    pipeline.sensor_profile = "vis_nir_research"
    pipeline.plant = "tomato"
    pipeline.classes = list(pipeline.classes_)
    
    print("\n5. Serializing Artifact...")
    model_path = MODELS_DIR / MODEL_FILENAME
    joblib.dump(pipeline, model_path)
    print(f"  Saved to: {model_path}")
    print(f"  File size: {model_path.stat().st_size / 1024:.2f} KB")
    
    print("\n6. Generating Final Report...")
    report = {
        "model_id": pipeline.model_id,
        "sensor_profile": pipeline.sensor_profile,
        "plant": pipeline.plant,
        "classes": pipeline.classes,
        "training_dataset": {
            "n_spectra": len(X_raw),
            "illumination": "PAR1000",
            "timepoints": ["d2", "d4", "d7", "d14"]
        },
        "artifact_path": str(model_path.resolve()),
        "status": "READY_FOR_INFERENCE",
        "expected_performance_reference": "Results/phase3a_candidate_feature_and_baseline_report.json"
    }
    
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    print(f"  Report saved to: {REPORT_JSON}")
    print("=" * 75)
    print("Phase 3B completed successfully.")

if __name__ == "__main__":
    main()

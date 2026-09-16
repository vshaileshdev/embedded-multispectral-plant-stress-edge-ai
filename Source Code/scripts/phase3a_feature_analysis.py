"""
Phase 3A — Candidate Feature Analysis & Leakage-Safe Baseline Modeling
======================================================================
Embedded Multispectral Plant Stress Differentiation System

Constraints strictly enforced:
1. Primary dataset: PAR1000 post-treatment (d2, d4, d7, d14; N=137).
2. d0 retained strictly as pre-treatment baseline reference.
3. Grouping variable: biological plant_id (18 unique plants).
4. Cross-validation: StratifiedGroupKFold (k=5) and LeaveOneGroupOut.
5. Candidate feature analysis before training (verifying wavelength availability,
   scientific relevance, and AS7341 compatibility).
6. Preprocessing, scaling, and feature extraction strictly inside cross-validation loops
   (fitted on training folds only).
7. Candidate baseline models evaluated: Logistic Regression, Random Forest, SVM.
8. Detailed fold-level metrics, per-class F1/precision/recall, and confusion matrices.
9. Formal documentation of AS7341 spectral simulation methodology (no AS7341 training yet).
10. Severity remains disabled.
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
from scipy.signal import savgol_filter

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedGroupKFold, LeaveOneGroupOut
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score, accuracy_score

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ─── Configuration & Paths ───────────────────────────────────────────────────

SCRIPT_DIR   = pathlib.Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RAW_DIR      = PROJECT_ROOT / "backend" / "data" / "raw" / "tomato"
RESULTS_DIR  = PROJECT_ROOT.parent / "Results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

REPORT_JSON  = RESULTS_DIR / "phase3a_candidate_feature_and_baseline_report.json"

TREATMENT_NAMES = {
    'c': 'Control (Healthy)',
    's': 'Water Deficit (Drought)',
    'n': 'Nitrogen Deficit'
}

# ─── AS7341 Discrete Channels (AMS Datasheet) ────────────────────────────────

AS7341_CHANNELS = {
    "F1": 415,
    "F2": 445,
    "F3": 480,
    "F4": 515,
    "F5": 555,
    "F6": 590,
    "F7": 630,
    "F8": 680,
    "NIR": 910,
}

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
        # d0 represents pre-treatment baseline. We exclude it from the stress classification
        # training population to prevent baseline ambiguity.
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


# ─── Candidate Spectral Indices Definition ────────────────────────────────────

CANDIDATE_INDICES = [
    {
        "name": "NDVI",
        "full_name": "Normalized Difference Vegetation Index",
        "category": "Chlorophyll / General Vigour",
        "formula": "(R800 - R670) / (R800 + R670)",
        "bands_needed_nm": [670, 800],
        "biological_relevance": "Standard canopy vigour index; sensitive to chlorophyll absorption and mesophyll scattering.",
        "as7341_compatibility": "Approximable using F8 (680 nm) and NIR (910 nm), though 910 nm is farther into NIR than standard 800 nm."
    },
    {
        "name": "GNDVI",
        "full_name": "Green Normalized Difference Vegetation Index",
        "category": "Chlorophyll / Nitrogen Status",
        "formula": "(R800 - R550) / (R800 + R550)",
        "bands_needed_nm": [550, 800],
        "biological_relevance": "More sensitive to higher chlorophyll concentrations than NDVI; strongly correlates with plant nitrogen content.",
        "as7341_compatibility": "Directly compatible: F5 (555 nm) provides the green reflectance peak; NIR (910 nm) provides NIR plateau."
    },
    {
        "name": "NDRE",
        "full_name": "Normalized Difference Red Edge Index",
        "category": "Chlorophyll / Early Nutrient Stress",
        "formula": "(R790 - R720) / (R790 + R720)",
        "bands_needed_nm": [720, 790],
        "biological_relevance": "Red-edge transition zone is sensitive to subtle chlorophyll changes before visible yellowing (chlorosis) appears.",
        "as7341_compatibility": "INCOMPATIBLE: AS7341 has no filter channel between 680 nm (F8) and 910 nm (NIR); cannot resolve the red-edge inflection."
    },
    {
        "name": "MCARI",
        "full_name": "Modified Chlorophyll Absorption in Reflectance Index",
        "category": "Chlorophyll Absorption Depth",
        "formula": "((R700 - R670) - 0.2 * (R700 - R550)) * (R700 / R670)",
        "bands_needed_nm": [550, 670, 700],
        "biological_relevance": "Measures depth of chlorophyll absorption at 670 nm relative to green and red-edge reflectance.",
        "as7341_compatibility": "PARTIAL: 555 nm (F5) and 680 nm (F8) available, but 700 nm boundary band is absent on AS7341."
    },
    {
        "name": "PSRI",
        "full_name": "Plant Senescence Reflectance Index",
        "category": "Carotenoid / Stress Senescence",
        "formula": "(R680 - R500) / R750",
        "bands_needed_nm": [500, 680, 750],
        "biological_relevance": "Tracks carotenoid-to-chlorophyll ratio. Increases sharply under drought stress and foliar senescence.",
        "as7341_compatibility": "PARTIAL: F8 (680 nm) available, F3/F4 (480/515 nm) approximates 500 nm, but 750 nm red-edge reference is absent."
    },
    {
        "name": "SIPI",
        "full_name": "Structure Intensive Pigment Index",
        "category": "Carotenoid / Photoprotective Dynamics",
        "formula": "(R800 - R445) / (R800 - R680)",
        "bands_needed_nm": [445, 680, 800],
        "biological_relevance": "Estimates carotenoids relative to chlorophyll under changing canopy structure; useful for drought stress assessment.",
        "as7341_compatibility": "Approximable using F2 (445 nm), F8 (680 nm), and NIR (910 nm)."
    },
    {
        "name": "CRI",
        "full_name": "Carotenoid Reflectance Index (CRI550)",
        "category": "Carotenoid Content",
        "formula": "(1 / R510) - (1 / R550)",
        "bands_needed_nm": [510, 550],
        "biological_relevance": "Direct measure of accessory carotenoid accumulation under photo-oxidative stress.",
        "as7341_compatibility": "Approximable: F4 (515 nm) and F5 (555 nm) match these absorption bands."
    },
    {
        "name": "ARI",
        "full_name": "Anthocyanin Reflectance Index",
        "category": "Anthocyanin / Stress Pigments",
        "formula": "(1 / R550) - (1 / R700)",
        "bands_needed_nm": [550, 700],
        "biological_relevance": "Sensitive to anthocyanin accumulation in stressed leaves.",
        "as7341_compatibility": "INCOMPATIBLE: 700 nm reference band absent on AS7341."
    },
    {
        "name": "WBI",
        "full_name": "Water Band Index",
        "category": "Foliar Water Status",
        "formula": "R900 / R970",
        "bands_needed_nm": [900, 970],
        "biological_relevance": "Ratios the 900 nm NIR baseline against the 970 nm liquid water absorption overtone. Directly correlates with relative leaf water content.",
        "as7341_compatibility": "INCOMPATIBLE: AS7341 NIR channel is centred at 910 nm; it does NOT measure the 970 nm water absorption band."
    },
    {
        "name": "RE_Slope",
        "full_name": "Red Edge Spectral Slope",
        "category": "Cellular & Chlorophyll Transition",
        "formula": "(R750 - R700) / 50.0",
        "bands_needed_nm": [700, 750],
        "biological_relevance": "Measures the steepness of the red-edge reflection inflection, which shifts towards shorter wavelengths under nutrient deficiency.",
        "as7341_compatibility": "INCOMPATIBLE: Requires high spectral resolution across 700–750 nm."
    }
]


# ─── Feature Extraction Transformer (Leakage-Safe) ──────────────────────────

class SpectralFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts candidate spectral indices and statistical regional band features
    from 832-channel reflectance vectors.
    """
    def __init__(self, wvl_grid):
        self.wvl_grid = np.asarray(wvl_grid)

    def _get_band_idx(self, target_nm):
        return int(np.argmin(np.abs(self.wvl_grid - target_nm)))

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = np.asarray(X)
        N = X.shape[0]
        features = []

        # Band indices
        idx_445 = self._get_band_idx(445)
        idx_500 = self._get_band_idx(500)
        idx_510 = self._get_band_idx(510)
        idx_550 = self._get_band_idx(550)
        idx_670 = self._get_band_idx(670)
        idx_680 = self._get_band_idx(680)
        idx_700 = self._get_band_idx(700)
        idx_720 = self._get_band_idx(720)
        idx_750 = self._get_band_idx(750)
        idx_790 = self._get_band_idx(790)
        idx_800 = self._get_band_idx(800)
        idx_900 = self._get_band_idx(900)
        idx_970 = self._get_band_idx(970)

        eps = 1e-8

        for i in range(N):
            spec = X[i]
            r445 = spec[idx_445]
            r500 = spec[idx_500]
            r510 = spec[idx_510]
            r550 = spec[idx_550]
            r670 = spec[idx_670]
            r680 = spec[idx_680]
            r700 = spec[idx_700]
            r720 = spec[idx_720]
            r750 = spec[idx_750]
            r790 = spec[idx_790]
            r800 = spec[idx_800]
            r900 = spec[idx_900]
            r970 = spec[idx_970]

            # 1. Candidate Indices
            ndvi  = (r800 - r670) / (r800 + r670 + eps)
            gndvi = (r800 - r550) / (r800 + r550 + eps)
            ndre  = (r790 - r720) / (r790 + r720 + eps)
            mcari = ((r700 - r670) - 0.2 * (r700 - r550)) * (r700 / (r670 + eps))
            psri  = (r680 - r500) / (r750 + eps)
            sipi  = (r800 - r445) / (r800 - r680 + eps)
            cri   = (1.0 / (r510 + eps)) - (1.0 / (r550 + eps))
            ari   = (1.0 / (r550 + eps)) - (1.0 / (r700 + eps))
            wbi   = r900 / (r970 + eps)
            re_slope = (r750 - r700) / 50.0

            # 2. Regional Statistical Bands
            vis_mean = np.mean(spec[(self.wvl_grid >= 400) & (self.wvl_grid <= 700)])
            re_mean  = np.mean(spec[(self.wvl_grid > 700) & (self.wvl_grid <= 740)])
            nir_mean = np.mean(spec[(self.wvl_grid > 740) & (self.wvl_grid <= 900)])
            nir_water_mean = np.mean(spec[(self.wvl_grid > 900) & (self.wvl_grid <= 1000)])

            row_feat = [
                ndvi, gndvi, ndre, mcari, psri, sipi, cri, ari, wbi, re_slope,
                vis_mean, re_mean, nir_mean, nir_water_mean
            ]
            features.append(row_feat)

        return np.array(features)


FEATURE_NAMES = [
    "NDVI", "GNDVI", "NDRE", "MCARI", "PSRI", "SIPI", "CRI", "ARI", "WBI", "RE_Slope",
    "VIS_Mean", "RedEdge_Mean", "NIR_Mean", "NIR_Water_Mean"
]


# ─── Baseline Cross-Validation Runner ────────────────────────────────────────

def evaluate_baseline_pipeline(X_raw, y, groups, wvl_grid):
    """
    Evaluates Logistic Regression, Random Forest, and SVM using StratifiedGroupKFold (k=5).
    Preprocessing (smoothing, feature extraction, standard scaling) is fitted STRICTLY on train folds.
    """
    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=2, random_state=42),
        "SVM_RBF": SVC(kernel='rbf', probability=True, random_state=42),
    }

    sgkf = StratifiedGroupKFold(n_splits=5)
    results = {}

    classes = ['c', 's', 'n']

    for name, clf in models.items():
        fold_metrics = []
        oof_preds = np.empty_like(y, dtype=object)
        oof_probs = np.zeros((len(y), len(classes)))

        for fold_idx, (train_idx, val_idx) in enumerate(sgkf.split(X_raw, y, groups)):
            # 1. Strict fold split
            X_train_raw, X_val_raw = X_raw[train_idx], X_raw[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            g_train, g_val = groups[train_idx], groups[val_idx]

            # 2. Savitzky-Golay smoothing (applied per spectrum)
            X_train_smooth = savgol_filter(X_train_raw, window_length=11, polyorder=2, axis=1)
            X_val_smooth   = savgol_filter(X_val_raw,   window_length=11, polyorder=2, axis=1)

            # 3. Feature extraction
            extractor = SpectralFeatureExtractor(wvl_grid)
            X_train_feat = extractor.transform(X_train_smooth)
            X_val_feat   = extractor.transform(X_val_smooth)

            # 4. Standard scaling fitted ONLY on train fold
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train_feat)
            X_val_scaled   = scaler.transform(X_val_feat)

            # 5. Fit model
            clf.fit(X_train_scaled, y_train)

            # 6. Predict on unseen validation plants
            y_pred = clf.predict(X_val_scaled)
            oof_preds[val_idx] = y_pred

            if hasattr(clf, "predict_proba"):
                oof_probs[val_idx] = clf.predict_proba(X_val_scaled)

            # Fold-level scores
            fold_f1_macro = f1_score(y_val, y_pred, average='macro')
            fold_acc = accuracy_score(y_val, y_pred)
            fold_metrics.append({
                "fold": fold_idx + 1,
                "val_plants": sorted(list(set(g_val))),
                "val_samples": len(val_idx),
                "macro_f1": round(float(fold_f1_macro), 4),
                "accuracy": round(float(fold_acc), 4),
            })

        # Overall Out-Of-Fold evaluation
        overall_macro_f1 = f1_score(y, oof_preds, average='macro')
        overall_acc = accuracy_score(y, oof_preds)
        report_dict = classification_report(y, oof_preds, target_names=[TREATMENT_NAMES[c] for c in classes], output_dict=True)
        cm = confusion_matrix(y, oof_preds, labels=classes).tolist()

        results[name] = {
            "overall_macro_f1": round(float(overall_macro_f1), 4),
            "overall_accuracy": round(float(overall_acc), 4),
            "fold_level_results": fold_metrics,
            "classification_report": report_dict,
            "confusion_matrix": {
                "labels": classes,
                "matrix": cm
            }
        }

    return results


# ─── Leave-One-Group-Out Runner for Baseline Comparison ──────────────────────

def evaluate_logocv(X_raw, y, groups, wvl_grid):
    """
    Evaluates RandomForest with LeaveOneGroupOut across all 18 biological plants.
    """
    logo = LeaveOneGroupOut()
    classes = ['c', 's', 'n']
    oof_preds = np.empty_like(y, dtype=object)

    for train_idx, val_idx in logo.split(X_raw, y, groups):
        X_train_raw, X_val_raw = X_raw[train_idx], X_raw[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        X_train_smooth = savgol_filter(X_train_raw, window_length=11, polyorder=2, axis=1)
        X_val_smooth   = savgol_filter(X_val_raw,   window_length=11, polyorder=2, axis=1)

        extractor = SpectralFeatureExtractor(wvl_grid)
        X_train_feat = extractor.transform(X_train_smooth)
        X_val_feat   = extractor.transform(X_val_smooth)

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_feat)
        X_val_scaled   = scaler.transform(X_val_feat)

        clf = RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=2, random_state=42)
        clf.fit(X_train_scaled, y_train)
        oof_preds[val_idx] = clf.predict(X_val_scaled)

    macro_f1 = f1_score(y, oof_preds, average='macro')
    cm = confusion_matrix(y, oof_preds, labels=classes).tolist()
    rep = classification_report(y, oof_preds, target_names=[TREATMENT_NAMES[c] for c in classes], output_dict=True)

    return {
        "macro_f1": round(float(macro_f1), 4),
        "classification_report": rep,
        "confusion_matrix": cm
    }


# ─── Main Execution ──────────────────────────────────────────────────────────

def main():
    print("=" * 75)
    print("PHASE 3A — CANDIDATE FEATURE ANALYSIS & BASELINE MODEL PIPELINE")
    print("Embedded Multispectral Plant Stress Differentiation System")
    print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)

    # 1. Dataset Loading
    df, wvl = load_post_treatment_dataset()
    print(f"\n1. DATASET PARTITION & SAMPLE UNIT VERIFICATION")
    print("-" * 75)
    print(f"  Primary Dataset: PAR1000 post-treatment (d2, d4, d7, d14)")
    print(f"  Observations:    N = {len(df)} spectra")
    print(f"  Spectral Bands:  {len(wvl)} channels ({wvl[0]:.2f}–{wvl[-1]:.2f} nm)")
    print(f"  Treatment Counts:")
    for t in ['c', 's', 'n']:
        n_t = int(np.sum(df['treatment'] == t))
        print(f"    - {TREATMENT_NAMES[t]:<26s}: {n_t} spectra")
    print(f"  Unique Biological Plants: {len(df['plant_id'].unique())} (6 per treatment group)")
    print(f"  Explicit Exclusion: d0 baseline spectra are held separate as reference data.")

    # 2. Candidate Feature Enumeration & Wavelength Verification
    print(f"\n2. CANDIDATE FEATURE ENUMERATION & WAVELENGTH VERIFICATION")
    print("-" * 75)
    feat_verification = []
    wvl_min, wvl_max = float(wvl[0]), float(wvl[-1])

    for idx_info in CANDIDATE_INDICES:
        req_bands = idx_info["bands_needed_nm"]
        available = all(wvl_min <= b <= wvl_max for b in req_bands)
        offsets = [float(np.min(np.abs(wvl - b))) for b in req_bands]
        max_offset = max(offsets)

        print(f"\n  [{idx_info['name']}] — {idx_info['full_name']}")
        print(f"    Category:             {idx_info['category']}")
        print(f"    Formula:              {idx_info['formula']}")
        print(f"    Bands required:       {req_bands} nm (max offset in dataset = {max_offset:.3f} nm)")
        print(f"    Wavelength Available: {'YES' if available else 'NO'}")
        print(f"    Biological Role:      {idx_info['biological_relevance']}")
        print(f"    AS7341 Compatibility: {idx_info['as7341_compatibility']}")

        feat_verification.append({
            "name": idx_info["name"],
            "available_in_dataset": available,
            "max_wavelength_offset_nm": round(max_offset, 3),
            "as7341_compatibility": idx_info["as7341_compatibility"],
            "biological_relevance": idx_info["biological_relevance"]
        })

    # Regional features
    print(f"\n  [Regional Band Statistics]")
    print(f"    - VIS_Mean:      Mean reflectance across 400–700 nm (chlorophyll & carotenoid absorption)")
    print(f"    - RedEdge_Mean:  Mean reflectance across 701–740 nm (red-edge inflection amplitude)")
    print(f"    - NIR_Mean:      Mean reflectance across 741–900 nm (mesophyll cellular scattering plateau)")
    print(f"    - NIR_Water_Mean: Mean reflectance across 901–1000 nm (contains 970 nm water absorption band)")

    # 3. Spectral Transformation / Simulation Method for AS7341
    print(f"\n3. AS7341 SPECTRAL TRANSFORMATION & SIMULATION METHODOLOGY")
    print("-" * 75)
    print(f"  The AS7341 has 9 discrete spectral channels (415, 445, 480, 515, 555, 590, 630, 680, 910 nm).")
    print(f"  To represent these dense spectra (832 bands) in AS7341 channel space without fabricating data:")
    print(f"    1. Spectral Response Function (SRF) Integration:")
    print(f"       Each channel response C_i is simulated via continuous convolution:")
    print(f"         C_i = integral [ R(lambda) * SRF_i(lambda) d_lambda ] / integral [ SRF_i(lambda) d_lambda ]")
    print(f"       where SRF_i(lambda) is the manufacturer optical filter transmission curve for channel i.")
    print(f"    2. Bandpass Approximation:")
    print(f"       If empirical SRFs are unverified, Gaussian approximations using the manufacturer FWHM")
    print(f"       (Full Width at Half Maximum ~20–30 nm) provide a standardized mathematical transformation.")
    print(f"    3. Decoupled Model Space:")
    print(f"       Models trained on full VIS-NIR cannot be called with AS7341 data. When the AS7341 model is built,")
    print(f"       it will be trained strictly on the transformed C_i feature vectors under its own model ID:")
    print(f"       'tomato_as7341_rf_v1.0.0'.")

    # 4. Leakage-Safe Baseline Model Evaluation
    print(f"\n4. LEAKAGE-SAFE BASELINE MODEL PIPELINE EVALUATION")
    print("-" * 75)
    print(f"  Pipeline Structure:")
    print(f"    Step 1: Savitzky-Golay Smoothing (w=11, p=2)")
    print(f"    Step 2: Candidate Spectral Feature Extraction (14 features)")
    print(f"    Step 3: StandardScaler (fitted on training folds only)")
    print(f"    Step 4: Classifier (fitted on training folds only)")
    print(f"  Validation Protocol: StratifiedGroupKFold (k=5, groups=plant_id)")

    X_raw = np.stack(df['refl'].values)
    y = df['treatment'].values
    groups = df['plant_id'].values

    cv_results = evaluate_baseline_pipeline(X_raw, y, groups, wvl)

    for model_name, res in cv_results.items():
        print(f"\n  ── MODEL: {model_name} ──")
        print(f"    Overall Out-Of-Fold Macro F1: {res['overall_macro_f1']:.4f}")
        print(f"    Overall Out-Of-Fold Accuracy: {res['overall_accuracy']:.4f}")
        print(f"    Fold-by-Fold Breakdown:")
        for fld in res['fold_level_results']:
            print(f"      Fold {fld['fold']}: Macro F1 = {fld['macro_f1']:.4f} | Acc = {fld['accuracy']:.4f} | "
                  f"Val Plants: {fld['val_plants']}")

        print(f"    Per-Class Classification Report:")
        rep = res['classification_report']
        for c in ['c', 's', 'n']:
            c_name = TREATMENT_NAMES[c]
            c_metrics = rep[c_name]
            print(f"      {c_name:<26s}: Precision = {c_metrics['precision']:.3f} | "
                  f"Recall = {c_metrics['recall']:.3f} | F1 = {c_metrics['f1-score']:.3f}")

        print(f"    Confusion Matrix (rows=True, cols=Pred; ['c', 's', 'n']):")
        cm = res['confusion_matrix']['matrix']
        for row, c in zip(cm, ['c', 's', 'n']):
            print(f"      True {c:<2s} ({TREATMENT_NAMES[c]:<24s}): {row}")

    # LOGOCV on best model (Random Forest)
    print(f"\n  ── LEAVE-ONE-GROUP-OUT CROSS-VALIDATION (Random Forest) ──")
    logo_res = evaluate_logocv(X_raw, y, groups, wvl)
    print(f"    Overall Leave-One-Plant-Out Macro F1: {logo_res['macro_f1']:.4f}")
    for c in ['c', 's', 'n']:
        c_name = TREATMENT_NAMES[c]
        c_met = logo_res['classification_report'][c_name]
        print(f"      {c_name:<26s}: F1 = {c_met['f1-score']:.3f} | Recall = {c_met['recall']:.3f}")
    print(f"    Confusion Matrix (LOGOCV):")
    for row, c in zip(logo_res['confusion_matrix'], ['c', 's', 'n']):
        print(f"      True {c:<2s}: {row}")

    # 5. Proposed Pipeline Summary & Save
    pipeline_summary = {
        "status": "CANDIDATE_ANALYSIS_COMPLETE_AWAITING_APPROVAL",
        "dataset": {
            "illumination": "PAR1000",
            "timepoints": ["d2", "d4", "d7", "d14"],
            "d0_status": "EXCLUDED_FROM_TRAINING_RETAINED_AS_REFERENCE",
            "n_spectra": len(df),
            "n_plants": len(np.unique(groups))
        },
        "candidate_features": feat_verification,
        "selected_feature_count": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "baseline_model_evaluations": cv_results,
        "leave_one_group_out_evaluation": logo_res,
        "severity_status": "DISABLED",
        "next_step": "Awaiting user review and authorization before final model training and artifact export"
    }

    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(pipeline_summary, f, indent=2)

    print(f"\nDetailed report saved to: {REPORT_JSON}")
    print("=" * 75)
    print("Phase 3A candidate feature analysis & baseline modeling completed.")
    print("STOPPED for user review and approval before final training/export.")

if __name__ == "__main__":
    main()

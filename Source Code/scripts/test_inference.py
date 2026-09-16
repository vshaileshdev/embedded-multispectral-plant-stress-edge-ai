"""
Test Inference Script
=====================
Validates that the saved model artifact can be loaded and handles inference correctly.
"""

import sys
import pathlib
import joblib
import numpy as np
from scipy.io import loadmat

# Add the parent directory to the path so we can import the backend module
SCRIPT_DIR = pathlib.Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Note: Even though we don't explicitly instantiate SpectralFeatureExtractor here,
# joblib will automatically resolve it because it's available in backend.ml.features
# provided the sys.path is correct (which it is for this script or the API).

MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "tomato_research_rf_v1.0.0.joblib"
RAW_FILE = PROJECT_ROOT / "backend" / "data" / "raw" / "tomato" / "2023_d2_Leaf_Spec_Tomato_Stress.mat"

def main():
    print("=" * 75)
    print("TEST INFERENCE SCRIPT")
    print("=" * 75)
    
    print("\n1. Loading Model Artifact...")
    try:
        pipeline = joblib.load(MODEL_PATH)
        print("  Model loaded successfully.")
    except Exception as e:
        print(f"  FAILED to load model: {e}")
        return
        
    print("\n2. Verifying Metadata...")
    print(f"  model_id: {getattr(pipeline, 'model_id', 'MISSING')}")
    print(f"  sensor_profile: {getattr(pipeline, 'sensor_profile', 'MISSING')}")
    print(f"  plant: {getattr(pipeline, 'plant', 'MISSING')}")
    print(f"  classes: {getattr(pipeline, 'classes', 'MISSING')}")
    
    if getattr(pipeline, 'sensor_profile', '') != 'vis_nir_research':
        print("  WARNING: sensor_profile mismatch!")
        
    print("\n3. Loading a Sample Spectrum...")
    try:
        mat = loadmat(str(RAW_FILE), struct_as_record=False, squeeze_me=False)
        p1000 = mat['PAR1000'][0, 0]
        refl = np.asarray(p1000.refl_real)
        # Take the very first spectrum
        sample = refl[0]
        print(f"  Sample loaded. Shape: {sample.shape}")
    except Exception as e:
        print(f"  FAILED to load sample data: {e}")
        return
        
    print("\n4. Running Inference...")
    # Scikit-learn pipelines expect 2D arrays for a single sample: (1, n_features)
    sample_2d = sample.reshape(1, -1)
    
    try:
        pred = pipeline.predict(sample_2d)
        probs = pipeline.predict_proba(sample_2d)
        
        print(f"  Prediction: {pred[0]}")
        print(f"  Probabilities: {dict(zip(pipeline.classes, probs[0]))}")
        print("  Inference SUCCESSFUL.")
    except Exception as e:
        print(f"  FAILED during inference: {e}")
        
    print("=" * 75)

if __name__ == "__main__":
    main()

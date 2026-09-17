import pathlib
import numpy as np
from scipy.io import loadmat
from fastapi import HTTPException

SCRIPT_DIR = pathlib.Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data" / "raw" / "tomato"

def get_dataset_spectrum(day: str = "d0"):
    """
    Loads the first spectrum from the specified experimental day's raw .mat file.
    """
    # Sanitize day input (e.g., 'D0' -> 'd0')
    safe_day = day.lower()
    
    filename = f"2023_{safe_day}_Leaf_Spec_Tomato_Stress.mat"
    filepath = DATA_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Dataset file {filename} not found.")
        
    try:
        mat = loadmat(str(filepath), struct_as_record=False, squeeze_me=False)
        p1000 = mat['PAR1000'][0, 0]
        refl = np.asarray(p1000.refl_real)
        
        if len(refl) == 0:
            raise HTTPException(status_code=400, detail="Dataset file contains no spectra.")
            
        return {
            "spectral_data": refl[0].tolist(),
            "sample_id": f"{filename}_idx0"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset spectrum: {str(e)}")

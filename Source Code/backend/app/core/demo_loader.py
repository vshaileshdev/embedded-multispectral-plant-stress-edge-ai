import pathlib
import numpy as np
from scipy.io import loadmat
from fastapi import HTTPException

SCRIPT_DIR = pathlib.Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data" / "raw" / "tomato"

def get_demo_spectrum(day: str = "d2", spectrum_index: int = 0):
    """
    Loads a spectrum from the raw .mat files to simulate a live measurement.
    """
    filename = f"2023_{day}_Leaf_Spec_Tomato_Stress.mat"
    filepath = DATA_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Demo file {filename} not found.")
        
    try:
        mat = loadmat(str(filepath), struct_as_record=False, squeeze_me=False)
        p1000 = mat['PAR1000'][0, 0]
        refl = np.asarray(p1000.refl_real)
        
        if spectrum_index >= len(refl):
            raise HTTPException(status_code=400, detail="Spectrum index out of bounds.")
            
        return refl[spectrum_index].tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load demo spectrum: {str(e)}")

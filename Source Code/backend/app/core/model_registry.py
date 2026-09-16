import joblib
import pathlib
import sys
from fastapi import HTTPException

# Ensure backend root is in sys.path so that ml.features can be resolved during unpickling
SCRIPT_DIR = pathlib.Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(BACKEND_DIR.parent))

MODELS_DIR = BACKEND_DIR / "models"

class ModelRegistry:
    def __init__(self):
        self._registry = {}
        self._load_initial_models()

    def _load_initial_models(self):
        """Pre-loads the supported models into memory."""
        # 1. Research Spectrometer Model
        tomato_rf_path = MODELS_DIR / "tomato_research_rf_v1.0.0.joblib"
        self._load_and_register(tomato_rf_path, 'tomato', 'vis_nir_research')
        
        # 2. Simulated AS7341 Edge Model
        tomato_as7341_path = MODELS_DIR / "tomato_as7341_rf_v1.0.0.joblib"
        self._load_and_register(tomato_as7341_path, 'tomato', 'as7341')

    def _load_and_register(self, path, default_plant, default_sensor):
        if path.exists():
            try:
                pipeline = joblib.load(path)
                plant = getattr(pipeline, 'plant', default_plant)
                sensor = getattr(pipeline, 'sensor_profile', default_sensor)
                self.register_model(plant, sensor, pipeline)
                print(f"Loaded model for {plant} + {sensor}: {getattr(pipeline, 'model_id', 'unknown')}")
            except Exception as e:
                print(f"Warning: Failed to load {path}: {e}")
        else:
            print(f"Warning: Model artifact not found at {path}")

    def register_model(self, plant_species: str, sensor_profile: str, model_pipeline):
        if plant_species not in self._registry:
            self._registry[plant_species] = {}
        self._registry[plant_species][sensor_profile] = model_pipeline

    def get_model(self, plant_species: str, sensor_profile: str):
        if plant_species not in self._registry:
            raise HTTPException(status_code=400, detail=f"Unsupported plant species: {plant_species}")
        if sensor_profile not in self._registry[plant_species]:
            raise HTTPException(status_code=400, detail=f"Unsupported sensor profile '{sensor_profile}' for plant '{plant_species}'")
        return self._registry[plant_species][sensor_profile]

# Singleton instance
model_registry = ModelRegistry()

# Embedded Multispectral Plant Stress Differentiation System Using Edge AI

## Project Status
Core Software MVP complete and verified.

## Current Capabilities
- Plant selection (Species and ID)
- Research-spectrum demo measurement loading
- Plant/sensor model registry
- Tomato research-spectrum ML inference
- Diagnosis with Model Confidence
- Measurement history tracking (SQLite)
- PDF diagnosis report generation
- Interactive Frontend (Vanilla JS SPA)
- FastAPI backend
- Automated backend and E2E tests

## Current Scientific Status
This project maintains strict scientific boundaries across three tiers:
1. **Research-spectrometer model**: The primary verified baseline (`vis_nir_research`), trained on the 832-channel PAR1000 dataset.
2. **Simulated AS7341-like model**: Unapproved / Pending Validation.
3. **Real physical AS7341 system**: Pending hardware integration.

*Note: The physical AS7341 model is NOT validated. Real hardware integration is still pending.*

## Scientific Limitations
- **Model confidence is NOT biological severity.** The confidence score represents statistical classification probability.
- Biological severity estimation is not currently supported in the MVP.
- Research-spectrum performance must not be presented as real AS7341 performance.
- Simulated AS7341 data is not equivalent to real sensor measurements.
- Physical AS7341 validation remains pending.

## Dependency Setup
This project uses Python 3.10+. It is recommended to use a virtual environment.

```bash
# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install production dependencies
cd "Source Code/backend"
pip install -r requirements.txt

# If you are developing or running tests, install dev dependencies
pip install -r requirements-dev.txt
```

## Dataset Setup
The repository **does not** contain the raw research `.mat` datasets due to their external origin. 
To run the demo spectrum pathways or retrain models:
1. Obtain the `2023_dX_Leaf_Spec_Tomato_Stress.mat` files (for d0, d2, d4, d7, d14).
2. Place them locally in the following directory:
   `Source Code/backend/data/raw/tomato/`

The API `/api/v1/demo/spectrum` and the training scripts expect the files to be located there.

## Model Files
The repository includes the following trained model artifacts (located in `Source Code/backend/models/`):
- `tomato_research_rf_v1.0.0.joblib`: The 14-feature Random Forest classifier expecting the 832-band `vis_nir_research` sensor profile.

## Running the Application
To run the full application (Backend + Frontend):

```bash
# Ensure you are in the backend directory
cd "Source Code/backend"

# Start the FastAPI server using Uvicorn
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Then, open your browser and navigate to: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## Testing
To run the backend test suite:
```bash
cd "Source Code/backend"
python -m pytest tests/test_api.py -v
```

To run the live End-to-End verification script (ensure the server is running first):
```bash
cd "Source Code/backend"
python e2e_test.py
```

## Project Structure
```text
.
├── .gitignore
├── README.md
├── Results/                      # Phase verification reports and metrics
└── Source Code/
    ├── scripts/                  # ML training and simulation scripts
    └── backend/                  # FastAPI Application
        ├── app/
        │   ├── api/              # HTTP Endpoints
        │   ├── core/             # Model Registry and Demo Loader
        │   ├── database/         # SQLite SQLAlchemy integration
        │   ├── diagnosis/        # Inference logic
        │   ├── reports/          # FPDF2 PDF Generation
        │   ├── schemas/          # Pydantic models
        │   └── main.py           # Application entrypoint
        ├── data/                 # Ignored raw dataset directory
        ├── models/               # Serialized .joblib artifacts
        ├── static/               # Frontend (HTML/JS/CSS)
        ├── tests/                # Pytest suites
        ├── e2e_test.py           # E2E runtime script
        ├── requirements.txt      # Production dependencies
        └── requirements-dev.txt  # Dev/Test dependencies
```

## Team Handoff
This repository is currently serving as a project checkpoint. Another developer can clone this repository, set up the virtual environment, install the dependencies, and run the Core Software MVP locally without requiring the external datasets (historical API/Frontend works entirely on pre-trained serialized models, and demo data can be mocked or added manually).

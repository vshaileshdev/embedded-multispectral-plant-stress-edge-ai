from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

from app.database.session import engine, Base
from app.api.endpoints import router as api_router
# Import model_registry to ensure it loads the initial models on startup
from app.core.model_registry import model_registry

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Plant Stress Detection API",
    description="Phase 4 Application Integration",
    version="1.0.0",
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Mount static files
SCRIPT_DIR = pathlib.Path(__file__).parent
STATIC_DIR = SCRIPT_DIR.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def read_root():
    return FileResponse(str(STATIC_DIR / "index.html"))

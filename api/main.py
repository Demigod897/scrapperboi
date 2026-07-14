from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import entities, search, stats, violations

app = FastAPI(
    title="scrapperboi API",
    description="Regulatory Problem Intelligence Engine for India",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(violations.router, prefix="/api/v1", tags=["violations"])
app.include_router(entities.router, prefix="/api/v1", tags=["entities"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])

app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")


@app.get("/")
async def root():
    return {
        "name": "scrapperboi",
        "version": "0.1.0",
        "description": "Regulatory Problem Intelligence Engine for India",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/scrape/{regulator_code}")
async def trigger_scrape(regulator_code: str):
    """Manually trigger a scrape for a regulator (e.g., 'rbi')."""
    try:
        from workers.tasks import run_scraper

        task = run_scraper.delay(regulator_code)
        return {
            "status": "queued",
            "task_id": task.id,
            "regulator": regulator_code,
            "message": f"Scrape for {regulator_code.upper()} has been queued. Check /api/v1/stats/scrape-runs for progress.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue scrape: {str(e)}")

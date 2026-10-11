
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

import config
from database import init_db
from auth_routes import router as auth_router
from medic_routes import router as medic_router
from patient_routes import router as patient_router
from templates import LOGIN_HTML
from templates_medic import MEDIC_DASHBOARD_HTML
from templates_patient import PATIENT_DASHBOARD_HTML

app = FastAPI(
    title="MedRec",
    version="3.0.0-phase3",
    docs_url=None if config.IS_PRODUCTION else "/docs",
    redoc_url=None if config.IS_PRODUCTION else "/redoc",
    openapi_url=None if config.IS_PRODUCTION else "/openapi.json",
)

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from rate_limit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.on_event("startup")
async def startup():
    init_db()

app.include_router(auth_router)
app.include_router(medic_router)
app.include_router(patient_router)


@app.get("/", response_class=HTMLResponse)
async def home():
    return LOGIN_HTML


@app.get("/medic", response_class=HTMLResponse)
async def medic_dashboard():
    return MEDIC_DASHBOARD_HTML


@app.get("/patient", response_class=HTMLResponse)
async def patient_dashboard():
    return PATIENT_DASHBOARD_HTML


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8080,
                reload=not config.IS_PRODUCTION)
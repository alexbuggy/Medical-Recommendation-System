
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from auth_routes import router as auth_router
from medic_routes import router as medic_router
from patient_routes import router as patient_router
from templates import LOGIN_HTML
from templates_medic import MEDIC_DASHBOARD_HTML
from templates_patient import PATIENT_DASHBOARD_HTML

app = FastAPI(title="MedRec", version="3.0.0-phase3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True)
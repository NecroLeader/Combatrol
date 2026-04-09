from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routers import battle, hardware, admin
from app.config import API_PREFIX, DOMAIN

app = FastAPI(
    title="Combatrol API",
    description="Battle idle simulator engine",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"https://{DOMAIN}", f"http://{DOMAIN}"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(battle.router,   prefix=API_PREFIX)
app.include_router(hardware.router, prefix=API_PREFIX)
app.include_router(admin.router,    prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


# Servir frontend estático — debe ir AL FINAL (captura todo lo que no matcheó antes)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

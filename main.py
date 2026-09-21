from typing import Annotated
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
from database import engine, SessionLocal
from router import auth, admin,driver, dashboard,booking
from router.auth import get_current_user


app = FastAPI()


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Database
# =========================

models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================
# Dependencies
# =========================

db_dependency = Annotated[
    Session,
    Depends(get_db)
]

user_dependency = Annotated[
    dict,
    Depends(get_current_user)
]


# =========================
# Routers
# =========================

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(driver.router)
app.include_router(dashboard.router)
app.include_router(booking.router)


# =========================
# Root Endpoint
# =========================

@app.get("/")
def root():
    return {
        "message": "Emergency Ambulance Dispatch System API is running"
    }


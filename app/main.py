"""
FastAPI Main Application Module

This module defines the main FastAPI application, including:
- Application initialization and configuration
- API endpoints for user authentication
- API endpoints for calculation management (BREAD operations)
- A compute-only endpoint for advanced operations (power, mod, etc.)
- Web routes for HTML templates
- Database table creation on startup
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import List

from fastapi import Body, FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

import uvicorn

# Application imports
from app.auth.dependencies import get_current_active_user
from app.models.calculation import Calculation
from app.models.user import User
from app.schemas.calculation import (
    CalculationBase,
    CalculationResponse,
    CalculationUpdate,
    CalculationOnlyResponse,   # NEW: response for compute-only
)
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.database import Base, get_db, engine

# NEW: compute helper that supports power/mod and other ops
from app.operations import compute


# ------------------------------------------------------------------------------
# Create tables on startup using the lifespan event
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    yield


app = FastAPI(
    title="Calculations API",
    description="API for managing calculations",
    version="1.0.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# Static Files and Templates Configuration
# ------------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ------------------------------------------------------------------------------
# Web (HTML) Routes
# ------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, tags=["web"])
def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse, tags=["web"])
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse, tags=["web"])
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse, tags=["web"])
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard/view/{calc_id}", response_class=HTMLResponse, tags=["web"])
def view_calculation_page(request: Request, calc_id: str):
    return templates.TemplateResponse("view_calculation.html", {"request": request, "calc_id": calc_id})

@app.get("/dashboard/edit/{calc_id}", response_class=HTMLResponse, tags=["web"])
def edit_calculation_page(request: Request, calc_id: str):
    return templates.TemplateResponse("edit_calculation.html", {"request": request, "calc_id": calc_id})

# ------------------------------------------------------------------------------
# Health
# ------------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def read_health():
    return {"status": "ok"}

# ------------------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------------------
@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(user_create: UserCreate, db: Session = Depends(get_db)):
    user_data = user_create.dict(exclude={"confirm_password"})
    try:
        user = User.register(db, user_data)
        db.commit()
        db.refresh(user)
        return user
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login_json(user_login: UserLogin, db: Session = Depends(get_db)):
    auth_result = User.authenticate(db, user_login.username, user_login.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = auth_result["user"]
    db.commit()

    expires_at = auth_result.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    return TokenResponse(
        access_token=auth_result["access_token"],
        refresh_token=auth_result["refresh_token"],
        token_type="bearer",
        expires_at=expires_at,
        user_id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
    )

@app.post("/auth/token", tags=["auth"])
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    auth_result = User.authenticate(db, form_data.username, form_data.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": auth_result["access_token"], "token_type": "bearer"}

# ------------------------------------------------------------------------------
# Calculations (BREAD)
# ------------------------------------------------------------------------------
@app.post("/calculations", response_model=CalculationResponse, status_code=status.HTTP_201_CREATED, tags=["calculations"])
def create_calculation(
    calculation_data: CalculationBase,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        new_calculation = Calculation.create(
            calculation_type=calculation_data.type,
            user_id=current_user.id,
            inputs=calculation_data.inputs,
        )
        new_calculation.result = new_calculation.get_result()

        db.add(new_calculation)
        db.commit()
        db.refresh(new_calculation)
        return new_calculation
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/calculations", response_model=List[CalculationResponse], tags=["calculations"])
def list_calculations(current_user = Depends(get_current_active_user), db: Session = Depends(get_db)):
    calculations = db.query(Calculation).filter(Calculation.user_id == current_user.id).all()
    return calculations

@app.get("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def get_calculation(calc_id: str, current_user = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")
    calculation = (
        db.query(Calculation)
        .filter(Calculation.id == calc_uuid, Calculation.user_id == current_user.id)
        .first()
    )
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")
    return calculation

@app.put("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def update_calculation(
    calc_id: str,
    calculation_update: CalculationUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")

    calculation = (
        db.query(Calculation)
        .filter(Calculation.id == calc_uuid, Calculation.user_id == current_user.id)
        .first()
    )
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    if calculation_update.inputs is not None:
        calculation.inputs = calculation_update.inputs
        calculation.result = calculation.get_result()

    calculation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(calculation)
    return calculation

@app.delete("/calculations/{calc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["calculations"])
def delete_calculation(calc_id: str, current_user = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")

    calculation = (
        db.query(Calculation)
        .filter(Calculation.id == calc_uuid, Calculation.user_id == current_user.id)
        .first()
    )
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    db.delete(calculation)
    db.commit()
    return None

# ------------------------------------------------------------------------------
# NEW: Compute-only endpoint (no DB writes) for advanced ops (power/mod/etc.)
# ------------------------------------------------------------------------------
@app.post("/calculations/compute", response_model=CalculationOnlyResponse, tags=["calculations"])
def compute_endpoint(req: CalculationBase):
    """
    Compute-only API for the additional calculation types.
    Accepts { type, inputs } and returns { result } with no DB writes.
    """
    return CalculationOnlyResponse(result=compute(req.type, req.inputs))

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="info")

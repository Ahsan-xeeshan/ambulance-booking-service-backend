from typing import Annotated, Optional
from datetime import timedelta, datetime, timezone
import os
from sqlalchemy import or_
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError

from database import SessionLocal
from models import (
    User,
    UserRole,
    Booking,
    Ambulance,
    BookingStatus,
)


router = APIRouter()


# =========================================================
# PASSWORD HASHING
# =========================================================

bcrypt_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# =========================================================
# JWT / OAUTH2
# =========================================================

OAuth2_bearer = OAuth2PasswordBearer(tokenUrl="/api/login/")

# For development this can have a fallback.
# In production, put SECRET_KEY in an environment variable.
SECRET_KEY = "gy4RbvpY1aT5dm3zAtFRXP7pTNX9a12V"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[
    Session,
    Depends(get_db)
]


# =========================================================
# SCHEMAS
# =========================================================

class CreateUser(BaseModel):
    email: str
    full_name: str
    username: str
    phone: str
    password: str
    address: Optional[str] = None

    # IMPORTANT:
    # Do NOT allow the public user to choose a role.
    # Every account created through public signup is a normal user.


class UpdateUser(BaseModel):
    username: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    full_name: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)


class UpdatePassword(BaseModel):
    current_password: str
    new_password: str


# =========================================================
# AUTHENTICATION
# =========================================================

def authenticate_user(
    db: Session,
    username: str,
    password: str
):
    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return False

    if not bcrypt_context.verify(
        password,
        user.password_hash
    ):
        return False

    return user


# =========================================================
# CREATE ACCESS TOKEN
# =========================================================

def create_access_token(
    username: str,
    user_id: str,
    role: str,
    expires_delta: timedelta
):
    expire = (
        datetime.now(timezone.utc)
        + expires_delta
    )

    payload = {
        "sub": username,
        "id": str(user_id),
        "role": role,
        "exp": expire
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user(
    token: Annotated[
        str,
        Depends(OAuth2_bearer)
    ]
):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")
        user_id = payload.get("id")
        role = payload.get("role")

        if (
            username is None
            or user_id is None
            or role is None
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )

        return {
            "username": username,
            "id": str(user_id),
            "role": role
        }

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


user_dependency = Annotated[
    dict,
    Depends(get_current_user)
]


# =========================================================
# ADMIN AUTHORIZATION
# =========================================================

def get_admin_user(
    current_user: user_dependency
):
    if current_user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user


admin_dependency = Annotated[
    dict,
    Depends(get_admin_user)
]


# =========================================================
# DRIVER AUTHORIZATION
# =========================================================

def get_driver_user(
    current_user: user_dependency
):
    if current_user.get("role") != UserRole.DRIVER.value:
        raise HTTPException(
            status_code=403,
            detail="Driver access required"
        )

    return current_user


driver_dependency = Annotated[
    dict,
    Depends(get_driver_user)
]


# =========================================================
# CREATE USER
# =========================================================

@router.post("/api/createuser/")
def create_users(
    db: db_dependency,
    new_user: CreateUser
):
    existing_user = db.query(User).filter(
    or_(
        User.username == new_user.username,
        User.email == new_user.email
    )
    ).first()

    if existing_user:
       raise HTTPException(
         status_code=400,
         detail="Username or email already registered"
       )

    user_model = User(
        email=new_user.email,
        username = new_user.username,
        full_name=new_user.full_name,
        phone=new_user.phone,
        address=new_user.address,
        password_hash=bcrypt_context.hash(
            new_user.password
        ),
        is_active=True,

        # Public signup can ONLY create normal users.
        role=UserRole.USER.value
    )

    db.add(user_model)
    db.commit()
    db.refresh(user_model)

    return {
        "message": "User created successfully",
        "user_id": user_model.id
    }


# =========================================================
# LOGIN
# =========================================================

@router.post("/api/login/")
def login_user(
    db: db_dependency,
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends()
    ]
):
    # OAuth2PasswordRequestForm calls the login field
   
    user = authenticate_user(
        db,
        form_data.username,
        form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    access_token = create_access_token(
        username=user.username,
        user_id=user.id,
        role=user.role,
        expires_delta=timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    return {
    "access_token": access_token,
    "token_type": "bearer",

    "user": {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role,
        "must_change_password": user.must_change_password,
    }
}


# =========================================================
# UPDATE USER
# =========================================================

@router.put("/api/edituser")
def update_user(
    user: user_dependency,
    db: db_dependency,
    update_user: UpdateUser
):
    user_model = db.query(User).filter(
        User.id == user.get("id")
    ).first()

    if user_model is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    update_data = update_user.model_dump(
        exclude_unset=True,
        exclude_none=True
    )

    # -----------------------------------------------------
    # Check email uniqueness
    # -----------------------------------------------------

    if "email" in update_data:
        existing_user = db.query(User).filter(
            User.email == update_data["email"],
            User.id != user_model.id
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

    # -----------------------------------------------------
    # Update fields
    # -----------------------------------------------------

    for key, value in update_data.items():
        setattr(user_model, key, value)

    db.commit()
    db.refresh(user_model)

    return {
        "message": "User updated successfully"
    }


# =========================================================
# CHANGE PASSWORD
# =========================================================

@router.put("/api/passwordchange")
def update_password(
    user: user_dependency,
    db: db_dependency,
    update_password: UpdatePassword
):
    user_model = db.query(User).filter(
        User.id == user.get("id")
    ).first()

    if user_model is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # -----------------------------------------------------
    # Verify old password
    # -----------------------------------------------------

    if not bcrypt_context.verify(
        update_password.current_password,
        user_model.password_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    # -----------------------------------------------------
    # Hash new password
    # -----------------------------------------------------

    user_model.password_hash = bcrypt_context.hash(
        update_password.new_password
    )

    # ----------------------------------------------------- 
    # Driver must no longer change password 
    # ----------------------------------------------------- 
    user_model.must_change_password = False

    db.commit()

    return {
        "message": "Password updated successfully"
    }


# =========================================================
# GET CURRENT USER
# =========================================================

@router.get("/api/user")
def get_user_details(
    user: user_dependency,
    db: db_dependency
):
    current_user = db.query(User).filter(
        User.id == user.get("id")
    ).first()

    if current_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    response = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "address": current_user.address,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "must_change_password": current_user.must_change_password,

        # Driver information
        "is_assigned": False,
        "assigned_trip": None,
        "assigned_ambulance": None,
    }

    # =====================================================
    # DRIVER INFORMATION
    # =====================================================

    if current_user.role == UserRole.DRIVER.value:

        # Find driver's active trip
        active_trip = (
            db.query(Booking)
            .filter(
                Booking.driver_id == current_user.id,
                Booking.status.in_([
                    BookingStatus.ASSIGNED.value,
                    BookingStatus.EN_ROUTE.value,
                ])
            )
            .order_by(
                Booking.assigned_time.desc()
            )
            .first()
        )

        if active_trip:

            response["is_assigned"] = True

            response["assigned_trip"] = {
                "id": active_trip.id,
                "patient_name": active_trip.patient_name,
                "patient_phone": active_trip.patient_phone,
                "pickup_address": active_trip.pickup_address,
                "dropoff_address": active_trip.dropoff_address,
                "status": active_trip.status,
                "booking_time": active_trip.booking_time,
                "assigned_time": active_trip.assigned_time,
            }

            # Get ambulance assigned to this trip
            if active_trip.ambulance_id:

                ambulance = db.query(Ambulance).filter(
                    Ambulance.id == active_trip.ambulance_id
                ).first()

                if ambulance:
                    response["assigned_ambulance"] = {
                        "id": ambulance.id,
                        "registration_number": (
                            ambulance.registration_number
                        ),
                        "ambulance_type": (
                            ambulance.ambulance_type
                        ),
                        "status": ambulance.status,
                    }

    return response
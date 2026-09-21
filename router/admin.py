from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import (
    User,
    UserRole,
    Ambulance,
    AmbulanceStatus,
    Booking,
    BookingStatus,
)

from router.auth import (
    admin_dependency,
    db_dependency,
    bcrypt_context,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
)


# =========================================================
# SCHEMAS
# =========================================================

class DriverCreate(BaseModel):
    username: str
    email: str
    full_name: str
    phone: str
    license_number: str
    license_expiry: Optional[datetime] = None



class AmbulanceCreate(BaseModel):
    registration_number: str
    ambulance_type: str


class BookingAssignRequest(BaseModel):
    ambulance_id: str
    driver_id: str


# =========================================================
# DRIVER MANAGEMENT
# =========================================================


@router.post("/drivers")
def create_driver(
    driver_data: DriverCreate,
    current_user: admin_dependency,
    db: db_dependency,
):
    """
    Admin creates a driver account.
    """

    # -----------------------------------------------------
    # Check email
    # -----------------------------------------------------

    existing_email = (
        db.query(User)
        .filter(User.email == driver_data.email, User.username == driver_data.username)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Username or Email already registered",
        )

    # -----------------------------------------------------
    # Check license number
    # -----------------------------------------------------

    existing_license = (
        db.query(User)
        .filter(
            User.license_number == driver_data.license_number
        )
        .first()
    )

    if existing_license:
        raise HTTPException(
            status_code=400,
            detail="License number already registered",
        )

    # -----------------------------------------------------
    # Temporary password
    # -----------------------------------------------------

    default_password = "driver123"

    # -----------------------------------------------------
    # Create driver
    # -----------------------------------------------------

    driver = User(
        username= driver_data.username,
        email=driver_data.email,
        full_name=driver_data.full_name,
        phone=driver_data.phone,

        password_hash=bcrypt_context.hash(
            default_password
        ),

        role=UserRole.DRIVER.value,

        license_number=driver_data.license_number,
        license_expiry=driver_data.license_expiry,

        is_active=True,

        # Driver must change password after first login
        must_change_password=True,
    )

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    db.add(driver)
    db.commit()
    db.refresh(driver)

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "id": driver.id,
        "username" : driver.username,
        "email": driver.email,
        "full_name": driver.full_name,
        "phone": driver.phone,
        "license_number": driver.license_number,
        "license_expiry": driver.license_expiry,
        "role": driver.role,

        "temporary_password": default_password,

        "message": (
            "Driver account created successfully. "
            "The driver should change the temporary password "
            "after first login."
        ),
    }


# =========================================================
# LIST DRIVERS
# =========================================================

@router.get("/drivers")
def list_drivers(
    current_user: admin_dependency,
    db: db_dependency,
):
    """
    Get all drivers with current trip status.
    """

    drivers = (
        db.query(User)
        .filter(
            User.role == UserRole.DRIVER.value
        )
        .order_by(
            User.created_at.desc()
        )
        .all()
    )

    result = []

    for driver in drivers:

        # Check if driver has an active trip
        active_trip = (
            db.query(Booking)
            .filter(
                Booking.driver_id == driver.id,
                Booking.status.in_([
                    BookingStatus.ASSIGNED,
                    BookingStatus.EN_ROUTE,
                ]),
            )
            .first()
        )

        result.append(
            {
                "id": driver.id,
                "email": driver.email,
                "full_name": driver.full_name,
                "phone": driver.phone,
                "license_number": driver.license_number,
                "license_expiry": driver.license_expiry,
                "is_active": driver.is_active,

                # Trip information
                "on_trip": active_trip is not None,

                "trip_status": (
                    active_trip.status
                    if active_trip
                    else None
                ),

                "booking_id": (
                    active_trip.id
                    if active_trip
                    else None
                ),
            }
        )

    return result

# =========================================================
# CREATE AMBULANCE
# =========================================================

@router.post("/ambulances")
def create_ambulance(
    ambulance_data: AmbulanceCreate,
    current_user: admin_dependency,
    db: db_dependency,
):
    """
    Add a new ambulance.
    """

    # -----------------------------------------------------
    # Check registration number
    # -----------------------------------------------------

    existing = (
        db.query(Ambulance)
        .filter(
            Ambulance.registration_number
            == ambulance_data.registration_number
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Registration number already exists"
        )

    # -----------------------------------------------------
    # Create ambulance
    # -----------------------------------------------------

    ambulance = Ambulance(
        registration_number=(
            ambulance_data.registration_number
        ),
        ambulance_type=(
            ambulance_data.ambulance_type
        ),
        status=AmbulanceStatus.AVAILABLE.value,
    )

    db.add(ambulance)
    db.commit()
    db.refresh(ambulance)

    return {
        "id": ambulance.id,
        "registration_number": ambulance.registration_number,
        "ambulance_type": ambulance.ambulance_type,
        "status": ambulance.status,
        "message": "Ambulance added successfully",
    }


# =========================================================
# LIST AMBULANCES
# =========================================================

@router.get("/ambulances")
def list_ambulances(
    current_user: admin_dependency,
    db: db_dependency,
):
    """
    Get all ambulances with assigned driver details.
    """

    ambulances = (
        db.query(Ambulance, User)
        .outerjoin(
            User,
            Ambulance.current_driver_id == User.id
        )
        .order_by(
            Ambulance.created_at.desc()
        )
        .all()
    )

    return [
        {
            "id": ambulance.id,
            "registration_number": ambulance.registration_number,
            "ambulance_type": ambulance.ambulance_type,
            "status": ambulance.status,
            "current_driver_id": ambulance.current_driver_id,
            "current_driver_name": (
                driver.full_name if driver else None, 
            ),
            "current_driver_phone": (
                driver.phone if driver else None,                
            ),
        }
        for ambulance, driver in ambulances
    ]

# =========================================================
# LIST ALL BOOKINGS
# =========================================================

@router.get("/bookings")
def list_all_bookings(
    current_user: admin_dependency,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(8, ge=1, le=100),
    db: db_dependency = None,
):
    query = db.query(Booking)

    # -----------------------------------------------------
    # Status filter
    # -----------------------------------------------------

    if status:
        valid_statuses = {
            item.value
            for item in BookingStatus
        }

        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid booking status"
            )

        query = query.filter(
            Booking.status == status
        )

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    if search and search.strip():
        search_term = f"%{search.strip()}%"

        query = query.filter(
            (Booking.patient_name.ilike(search_term))
            | (Booking.patient_phone.ilike(search_term))
            | (Booking.pickup_address.ilike(search_term))
            | (Booking.dropoff_address.ilike(search_term))
        )

    # -----------------------------------------------------
    # Total records
    # -----------------------------------------------------

    total = query.count()

    # -----------------------------------------------------
    # Pagination
    # -----------------------------------------------------

    skip = (page - 1) * limit

    bookings = (
        query
        .order_by(
            Booking.booking_time.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    # -----------------------------------------------------
    # Total pages
    # -----------------------------------------------------

    total_pages = (
        (total + limit - 1) // limit
        if total > 0
        else 1
    )

    # -----------------------------------------------------
    # Build response
    # -----------------------------------------------------

    booking_list = []

    for booking in bookings:

        # ---------------------------------------------
        # Find ambulance
        # ---------------------------------------------

        ambulance = None

        if booking.ambulance_id:
            ambulance = (
                db.query(Ambulance)
                .filter(
                    Ambulance.id == booking.ambulance_id
                )
                .first()
            )

        # ---------------------------------------------
        # Find driver
        # ---------------------------------------------

        driver = None

        if booking.driver_id:
            driver = (
                db.query(User)
                .filter(
                    User.id == booking.driver_id
                )
                .first()
            )

        # ---------------------------------------------
        # Add booking
        # ---------------------------------------------

        booking_list.append({
            "id": booking.id,

            "patient_name": booking.patient_name,
            "patient_phone": booking.patient_phone,

            "pickup_address": booking.pickup_address,
            "dropoff_address": booking.dropoff_address,

            "status": booking.status,

            "ambulance_id": booking.ambulance_id,
            "ambulance_registration_number": (
                ambulance.registration_number
                if ambulance
                else None
            ),

            "driver_id": booking.driver_id,
            "driver_name": (
                driver.full_name
                if driver
                else None
            ),
            "driver_phone": (
                driver.phone
                if driver
                else None
            ),

            "booking_time": booking.booking_time,
            "assigned_time": booking.assigned_time,
            "completed_time": booking.completed_time,
        })

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "bookings": booking_list,

        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }
    }

# =========================================================
# SINGLE BOOKING INFO
# =========================================================


@router.get("/bookings/{booking_id}")
def get_booking_details(
    booking_id: str,
    current_user: admin_dependency,
    db: db_dependency,
):
    """
    Get complete details of a single booking.
    """

    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .first()
    )

    if not booking:

        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    # ---------------------------------------------------------
    # Driver
    # ---------------------------------------------------------

    driver_name = None

    if booking.driver_id:
        driver = (
            db.query(User)
            .filter(User.id == booking.driver_id)
            .first()
        )

        if driver:
            driver_name = driver.full_name

    # ---------------------------------------------------------
    # Ambulance
    # ---------------------------------------------------------

    ambulance_registration_number = None

    if booking.ambulance_id:
        ambulance = (
            db.query(Ambulance)
            .filter(Ambulance.id == booking.ambulance_id)
            .first()
        )

        if ambulance:
            ambulance_registration_number = (
                ambulance.registration_number
            )
            ambulance_type = (
                ambulance.ambulance_type
            )

    # ---------------------------------------------------------
    # Response
    # ---------------------------------------------------------

    return {
        "id": booking.id,
        "status": booking.status.value
        if hasattr(booking.status, "value")
        else booking.status,

        "booking_time": booking.booking_time,

        "patient_name": booking.patient_name,
        "patient_phone": booking.patient_phone,

        "pickup_address": booking.pickup_address,
        "dropoff_address": booking.dropoff_address,

        "driver_name": driver_name,

        "ambulance_registration_number": (
            ambulance_registration_number
        ),
        "ambulance_type": (
             ambulance_type
        ),

        "assigned_at": booking.assigned_time,
    }

# =========================================================
# ASSIGN BOOKING
# =========================================================

@router.post("/bookings/{booking_id}/assign")
def assign_booking(
    booking_id: str,
    assign_data: BookingAssignRequest,
    current_user: admin_dependency,
    db: db_dependency,
):
    """
    Assign an available ambulance and active driver
    to a pending booking.
    """

    # -----------------------------------------------------
    # Find booking
    # -----------------------------------------------------

    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .first()
    )

    if booking is None:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    # -----------------------------------------------------
    # Booking must be pending
    # -----------------------------------------------------

    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail="Only pending bookings can be assigned"
        )

    # -----------------------------------------------------
    # Find ambulance
    # -----------------------------------------------------

    ambulance = (
        db.query(Ambulance)
        .filter(Ambulance.id == assign_data.ambulance_id)
        .first()
    )

    if ambulance is None:
        raise HTTPException(
            status_code=404,
            detail="Ambulance not found"
        )

    # -----------------------------------------------------
    # Ambulance must be available
    # -----------------------------------------------------

    if ambulance.status != AmbulanceStatus.AVAILABLE.value:
        raise HTTPException(
            status_code=400,
            detail="Selected ambulance is not available"
        )

    # -----------------------------------------------------
    # Find driver
    # -----------------------------------------------------

    driver = (
        db.query(User)
        .filter(
            User.id == assign_data.driver_id,
            User.role == UserRole.DRIVER.value,
        )
        .first()
    )

    if driver is None:
        raise HTTPException(
            status_code=404,
            detail="Driver not found"
        )

    # -----------------------------------------------------
    # Driver must be active
    # -----------------------------------------------------

    if not driver.is_active:
        raise HTTPException(
            status_code=400,
            detail="Selected driver is inactive"
        )

    # -----------------------------------------------------
    # Driver must not have an active booking
    # -----------------------------------------------------

    active_booking = (
        db.query(Booking)
        .filter(
            Booking.driver_id == driver.id,
            Booking.status.in_([
                BookingStatus.ASSIGNED.value,
                BookingStatus.EN_ROUTE.value,
            ])
        )
        .first()
    )

    if active_booking:
        raise HTTPException(
            status_code=400,
            detail="This driver already has an active booking"
        )

    # -----------------------------------------------------
    # Assign driver and ambulance
    # -----------------------------------------------------

    booking.ambulance_id = ambulance.id
    booking.driver_id = driver.id
    booking.status = BookingStatus.ASSIGNED.value
    booking.assigned_time = datetime.now(timezone.utc)

    # -----------------------------------------------------
    # Update ambulance
    # -----------------------------------------------------

    ambulance.status = AmbulanceStatus.BUSY.value
    ambulance.current_driver_id = driver.id

    # -----------------------------------------------------
    # Save changes
    # -----------------------------------------------------

    try:
        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to assign booking"
        )

    # -----------------------------------------------------
    # Refresh objects
    # -----------------------------------------------------

    db.refresh(booking)
    db.refresh(ambulance)

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "booking_id": booking.id,
        "status": booking.status,

        "ambulance": {
            "id": ambulance.id,
            "registration_number": ambulance.registration_number,
        },

        "driver": {
            "id": driver.id,
            "name": driver.full_name,
        },

        "assigned_time": booking.assigned_time,

        "message": "Booking assigned successfully",
    }

# temporary admin creation

class AdminCreate(BaseModel):
    username: str
    email: str
    full_name: str
    phone: str
    password: str


@router.post("/create-first-admin")
def create_first_admin(
    admin_data: AdminCreate,
    db: db_dependency,
):
    # Check whether an admin already exists
    existing_admin = (
        db.query(User)
        .filter(
            User.role == UserRole.ADMIN.value
        )
        .first()
    )

    if existing_admin:
        raise HTTPException(
            status_code=400,
            detail="An admin account already exists"
        )

    # Check email
    existing_user = (
        db.query(User)
        .filter(
            User.email == admin_data.email
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Create admin
    admin = User(
        email=admin_data.email,
        full_name=admin_data.full_name,
        username = admin_data.username,
        phone=admin_data.phone,
        password_hash=bcrypt_context.hash(
            admin_data.password
        ),
        role=UserRole.ADMIN.value,
        is_active=True,
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return {
        "id": admin.id,
        "username" : admin.username,
        "email": admin.email,
        "full_name": admin.full_name,
        "phone": admin.phone,
        "role": admin.role,
        "message": "Admin account created successfully",
    }
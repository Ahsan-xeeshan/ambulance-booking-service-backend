from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from models import Booking, BookingStatus, User, Ambulance
from router.auth import user_dependency, db_dependency


router = APIRouter(
    prefix="/api/bookings",
    tags=["Bookings"],
)


# ============================================================================
# CREATE BOOKING
# ============================================================================

class BookingCreate(BaseModel):
    patient_name: str = Field(..., min_length=2, max_length=100)
    patient_phone: str = Field(..., min_length=5, max_length=20)

    pickup_address: str = Field(..., min_length=5, max_length=500)
    dropoff_address: str = Field(..., min_length=5, max_length=500)

   

@router.post("", status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_data: BookingCreate,
    current_user: user_dependency,
    db: db_dependency,
):
    """
    Create a new ambulance booking.
    """

    booking = Booking(
        user_id=current_user["id"],
        patient_name=booking_data.patient_name,
        patient_phone=booking_data.patient_phone,
        pickup_address=booking_data.pickup_address,
        dropoff_address=booking_data.dropoff_address,
        status=BookingStatus.PENDING,
        booking_time=datetime.now(timezone.utc),
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "message": "Booking created successfully",
        "booking": {
            "id": booking.id,
            "patient_name": booking.patient_name,
            "patient_phone": booking.patient_phone,
            "pickup_address": booking.pickup_address,
            "dropoff_address": booking.dropoff_address,
            "status": booking.status,
            "booking_time": booking.booking_time,
        },
    }


# ============================================================================
# GET MY BOOKINGS
# ============================================================================

@router.get("/my-bookings")
def get_my_bookings(
    current_user: user_dependency,
    db: db_dependency,
):
    """
    Get all bookings created by the logged-in user.
    """

    bookings = (
        db.query(Booking)
        .filter(
            Booking.user_id == current_user["id"]
        )
        .order_by(
            Booking.booking_time.desc()
        )
        .all()
    )

    result = []

    for booking in bookings:

        # -----------------------------------------
        # Get driver
        # -----------------------------------------
        driver = None

        if booking.driver_id:
            driver = (
                db.query(User)
                .filter(
                    User.id == booking.driver_id
                )
                .first()
            )

        # -----------------------------------------
        # Get ambulance
        # -----------------------------------------
        ambulance = None

        if booking.ambulance_id:
            ambulance = (
                db.query(Ambulance)
                .filter(
                    Ambulance.id == booking.ambulance_id
                )
                .first()
            )

        # -----------------------------------------
        # Booking response
        # -----------------------------------------
        result.append({
            "id": booking.id,

            "patient_name": booking.patient_name,
            "patient_phone": booking.patient_phone,

            "pickup_address": booking.pickup_address,
            "dropoff_address": booking.dropoff_address,

            "status": booking.status,

            "booking_time": booking.booking_time,
            "assigned_time": booking.assigned_time,
            "completed_time": booking.completed_time,

            # IDs
            "driver_id": booking.driver_id,
            "ambulance_id": booking.ambulance_id,

            # Display information
            "driver_name": driver.full_name if driver else None,
            "driver_phone": driver.phone if driver else None,
            "ambulance_number": (
                ambulance.registration_number
                if ambulance
                else None
            ),
            "ambulance_type":(ambulance.ambulance_type if ambulance else None),
        })

    return {
        "bookings": result
    }



# ============================================================================
# CANCEL MY BOOKING
# ============================================================================

@router.delete("/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    current_user: user_dependency,
    db: db_dependency,
):
    """
    Cancel a booking created by the logged-in user.
    """

    # ---------------------------------------------------------
    # Find booking belonging to current user
    # ---------------------------------------------------------

    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.user_id == current_user["id"],
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # ---------------------------------------------------------
    # Only pending bookings can be cancelled
    # ---------------------------------------------------------

    if booking.status != BookingStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending bookings can be cancelled",
        )

    # ---------------------------------------------------------
    # Cancel booking
    # ---------------------------------------------------------

    booking.status = BookingStatus.CANCELLED

    db.commit()
    db.refresh(booking)

    return {
        "message": "Booking cancelled successfully",
        "booking": {
            "id": booking.id,
            "patient_name": booking.patient_name,
            "patient_phone": booking.patient_phone,
            "pickup_address": booking.pickup_address,
            "dropoff_address": booking.dropoff_address,
            "status": booking.status,
            "booking_time": booking.booking_time,
        },
    }
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import (
    Booking,
    Ambulance,
    BookingStatus,
    AmbulanceStatus,
)

from router.auth import (
    driver_dependency,
    db_dependency,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/driver",
    tags=["Driver"],
)


# =========================================================
# SCHEMAS
# =========================================================

class BookingStatusUpdate(BaseModel):
    status: BookingStatus


# =========================================================
# GET ASSIGNED BOOKINGS
# =========================================================

@router.get("/assigned-bookings")
def driver_assigned_bookings(
    current_user: driver_dependency,
    db: db_dependency,
):
    """
    Get all active bookings assigned to the logged-in driver.
    """

    bookings = (
        db.query(Booking)
        .filter(
            Booking.driver_id == current_user["id"],
            Booking.status.in_([
                BookingStatus.ASSIGNED.value,
                BookingStatus.EN_ROUTE.value,
                BookingStatus.COMPLETED.value,
            ]),
        )
        .order_by(
            Booking.assigned_time.desc()
        )
        .all()
    )

    return [
        {
            # Database ID
            "id": booking.id,

            # Patient information
            "patient_name": booking.patient_name,
            "patient_phone": booking.patient_phone,

            # Trip addresses
            "pickup_address": booking.pickup_address,
            "dropoff_address": booking.dropoff_address,

            # Booking status
            "status": booking.status,

            # Ambulance information
            "ambulance_number": (
                booking.ambulance.registration_number
                if booking.ambulance
                else None
            ),
            "ambulance_type": (
                booking.ambulance.ambulance_type
                if booking.ambulance
                else None
            ),

            # Times
            "booking_time": booking.booking_time,
            "assigned_time": booking.assigned_time,
        }
        for booking in bookings
    ]

# =========================================================
# UPDATE BOOKING STATUS
# =========================================================

@router.put("/bookings/{booking_id}/update-status")
def update_booking_status(
    booking_id: str,
    status_update: BookingStatusUpdate,
    current_user: driver_dependency,
    db: db_dependency,
):
    """
    Update the status of a booking assigned to the driver.

    Allowed transitions:

        ASSIGNED -> EN_ROUTE
        EN_ROUTE -> COMPLETED
    """

    # -----------------------------------------------------
    # Find booking
    # -----------------------------------------------------

    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id
        )
        .first()
    )

    if booking is None:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    # -----------------------------------------------------
    # Check assigned driver
    # -----------------------------------------------------

    if booking.driver_id != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Only the assigned driver can update this booking"
        )

    # -----------------------------------------------------
    # Valid status transitions
    # -----------------------------------------------------

    valid_transitions = {
        BookingStatus.ASSIGNED.value:
            BookingStatus.EN_ROUTE.value,

        BookingStatus.EN_ROUTE.value:
            BookingStatus.COMPLETED.value,
    }

    current_status = booking.status
    new_status = status_update.status.value

    expected_status = valid_transitions.get(
        current_status
    )

    if expected_status != new_status:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status transition: "
                f"{current_status} -> {new_status}"
            )
        )

    # -----------------------------------------------------
    # Update booking status
    # -----------------------------------------------------

    booking.status = new_status

    # -----------------------------------------------------
    # If completed
    # -----------------------------------------------------

    if new_status == BookingStatus.COMPLETED.value:

        booking.completed_time = datetime.now(
            timezone.utc
        )

        # Make the ambulance available again
        if booking.ambulance_id:

            ambulance = (
                db.query(Ambulance)
                .filter(
                    Ambulance.id == booking.ambulance_id
                )
                .first()
            )

            if ambulance:
                ambulance.status = (
                    AmbulanceStatus.AVAILABLE.value
                )

                # Remove the driver from the ambulance
                if (
                    ambulance.current_driver_id
                    == current_user["id"]
                ):
                    ambulance.current_driver_id = None

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    db.commit()
    db.refresh(booking)

    return {
        "booking_id": booking.id,
        "status": booking.status,
        "message": (
            f"Booking status updated to "
            f"{booking.status}"
        )
    }


# =========================================================
# GET COMPLETED TRIPS
# =========================================================

@router.get("/completed-trips")
def driver_completed_trips(
    current_user: driver_dependency,
    db: db_dependency,
):
    """
    Get completed trips of the logged-in driver.
    """

    bookings = (
        db.query(Booking)
        .filter(
            Booking.driver_id == current_user["id"],
            Booking.status == BookingStatus.COMPLETED.value,
        )
        .order_by(
            Booking.completed_time.desc()
        )
        .all()
    )

    return [
        {
            "id": booking.id,
            "patient_name": booking.patient_name,
            "patient_phone": booking.patient_phone,

            "pickup_address": booking.pickup_address,
            "dropoff_address": booking.dropoff_address,

            "status": booking.status,

            "ambulance_number": (
                booking.ambulance.registration_number
                if booking.ambulance
                else None
            ),

            "booking_time": booking.booking_time,
            "assigned_time": booking.assigned_time,
            "completed_time": booking.completed_time,
        }
        for booking in bookings
    ]


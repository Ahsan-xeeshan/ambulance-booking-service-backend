from datetime import datetime, timezone

from database import SessionLocal
from models import Booking, BookingStatus


def create_booking(
    customer_id: str,
    patient_name: str,
    patient_phone: str,
    pickup_address: str,
    dropoff_address: str,
):
    db = SessionLocal()

    try:
        booking = Booking(
            user_id=customer_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
            status=BookingStatus.PENDING,
            booking_time=datetime.now(timezone.utc),
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        return {
            "success": True,
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

    except Exception as e:

        db.rollback()

        return {
            "success": False,
            "error": str(e)
        }

    finally:
        db.close()
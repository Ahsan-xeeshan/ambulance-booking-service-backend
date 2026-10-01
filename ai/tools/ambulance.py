from database import SessionLocal
from models import Ambulance


def check_availability():

    db = SessionLocal()

    try:
        ambulances = (
            db.query(Ambulance)
            .filter(
                Ambulance.status == "available"
            )
            .all()
        )

        return {
            "success": True,
            "ambulances": [
                {
                    "id": ambulance.id,
                    "registration_number": ambulance.registration_number,
                    "ambulance_type": ambulance.ambulance_type,
                    "status": ambulance.status
                }
                for ambulance in ambulances
            ]
        }

    finally:
        db.close()
from database import SessionLocal
from models import User


def get_customer(customer_id: str):

    db = SessionLocal()

    try:
        customer = (
            db.query(User)
            .filter(
                User.id == customer_id,
                User.role == "user"
            )
            .first()
        )

        if not customer:
            return {
                "success": False,
                "error": "Customer not found."
            }

        return {
            "success": True,
            "customer": {
                "id": customer.id,
                "username": customer.username,
                "full_name": customer.full_name,
                "email": customer.email,
                "phone": customer.phone,
                "address": customer.address
            }
        }

    finally:
        db.close()
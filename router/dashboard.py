from fastapi import APIRouter,HTTPException

from models import (
    UserRole,
    BookingStatus,
    AmbulanceStatus,
    Booking,
    Ambulance,
    User,
)

from router.auth import (
    user_dependency,
    db_dependency,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


# =========================================================
# DASHBOARD STATISTICS
# =========================================================

@router.get("/stats")
def dashboard_stats(
    current_user: user_dependency,
    db: db_dependency,
):
    """
    Return dashboard statistics based on the
    logged-in user's role.

    ADMIN  -> System-wide statistics
    USER   -> Own booking statistics
    DRIVER -> Assigned/completed trip statistics
    """

    user_id = current_user["id"]
    role = current_user["role"]

    # =====================================================
    # ADMIN DASHBOARD
    # =====================================================

    if role == UserRole.ADMIN.value:

        total_bookings = (
            db.query(Booking).count()
        )

        pending_bookings = (
            db.query(Booking)
            .filter(
                Booking.status
                == BookingStatus.PENDING.value
            )
            .count()
        )

        assigned_bookings = (
            db.query(Booking)
            .filter(
                Booking.status
                == BookingStatus.ASSIGNED.value
            )
            .count()
        )

        en_route_bookings = (
            db.query(Booking)
            .filter(
                Booking.status
                == BookingStatus.EN_ROUTE.value
            )
            .count()
        )

        completed_bookings = (
            db.query(Booking)
            .filter(
                Booking.status
                == BookingStatus.COMPLETED.value
            )
            .count()
        )

        total_ambulances = (
            db.query(Ambulance).count()
        )

        available_ambulances = (
            db.query(Ambulance)
            .filter(
                Ambulance.status
                == AmbulanceStatus.AVAILABLE.value
            )
            .count()
        )

        busy_ambulances = (
            db.query(Ambulance)
            .filter(
                Ambulance.status
                == AmbulanceStatus.BUSY.value
            )
            .count()
        )

        maintenance_ambulances = (
            db.query(Ambulance)
            .filter(
                Ambulance.status
                == AmbulanceStatus.MAINTENANCE.value
            )
            .count()
        )

        total_drivers = (
            db.query(User)
            .filter(
                User.role
                == UserRole.DRIVER.value
            )
            .count()
        )

        active_drivers = (
            db.query(User)
            .filter(
                User.role
                == UserRole.DRIVER.value,
                User.is_active == True,
            )
            .count()
        )

        return {
            "total_bookings": total_bookings,

            "pending_bookings": pending_bookings,
            "assigned_bookings": assigned_bookings,
            "en_route_bookings": en_route_bookings,
            "completed_bookings": completed_bookings,

            "total_ambulances": total_ambulances,
            "available_ambulances": available_ambulances,
            "busy_ambulances": busy_ambulances,
            "maintenance_ambulances": (
                maintenance_ambulances
            ),

            "total_drivers": total_drivers,
            "active_drivers": active_drivers,
        }

    # =====================================================
    # USER DASHBOARD
    # =====================================================

    elif role == UserRole.USER.value:

        total_bookings = (
            db.query(Booking)
            .filter(
                Booking.user_id == user_id
            )
            .count()
        )

        pending_bookings = (
            db.query(Booking)
            .filter(
                Booking.user_id == user_id,
                Booking.status
                == BookingStatus.PENDING.value,
            )
            .count()
        )

        assigned_bookings = (
            db.query(Booking)
            .filter(
                Booking.user_id == user_id,
                Booking.status
                == BookingStatus.ASSIGNED.value,
            )
            .count()
        )

        en_route_bookings = (
            db.query(Booking)
            .filter(
                Booking.user_id == user_id,
                Booking.status
                == BookingStatus.EN_ROUTE.value,
            )
            .count()
        )

        completed_bookings = (
            db.query(Booking)
            .filter(
                Booking.user_id == user_id,
                Booking.status
                == BookingStatus.COMPLETED.value,
            )
            .count()
        )

        cancelled_bookings = (
            db.query(Booking)
            .filter(
                Booking.user_id == user_id,
                Booking.status
                == BookingStatus.CANCELLED.value,
            )
            .count()
        )

        return {
            "total_bookings": total_bookings,

            "pending_bookings": pending_bookings,
            "assigned_bookings": assigned_bookings,
            "en_route_bookings": en_route_bookings,
            "completed_bookings": completed_bookings,
            "cancelled_bookings": cancelled_bookings,
        }

    # =====================================================
    # DRIVER DASHBOARD
    # =====================================================

    elif role == UserRole.DRIVER.value:

        assigned_bookings = (
            db.query(Booking)
            .filter(
                Booking.driver_id == user_id,
                Booking.status.in_([
                    BookingStatus.ASSIGNED.value,
                    BookingStatus.EN_ROUTE.value,
                ])
            )
            .count()
        )

        en_route_bookings = (
            db.query(Booking)
            .filter(
                Booking.driver_id == user_id,
                Booking.status
                == BookingStatus.EN_ROUTE.value,
            )
            .count()
        )

        completed_bookings = (
            db.query(Booking)
            .filter(
                Booking.driver_id == user_id,
                Booking.status
                == BookingStatus.COMPLETED.value,
            )
            .count()
        )

        return {
            "assigned_bookings": assigned_bookings,
            "en_route_bookings": en_route_bookings,
            "completed_bookings": completed_bookings,
        }

    # =====================================================
    # UNKNOWN ROLE
    # =====================================================

    raise HTTPException(
        status_code=403,
        detail="Invalid user role"
    )


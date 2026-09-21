from database import Base

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Boolean,
    Float,
    DateTime,
)

from sqlalchemy.orm import relationship

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, PyEnum):
    ADMIN = "admin"
    USER = "user"
    DRIVER = "driver"


class BookingStatus(str, PyEnum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AmbulanceStatus(str, PyEnum):
    AVAILABLE = "available"
    BUSY = "busy"
    MAINTENANCE = "maintenance"


# ============================================================================
# USER MODEL
# ============================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    email = Column(
        String,
        unique=True,
        index=True
    )

    username = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    full_name = Column(String)

    phone = Column(String)

    password_hash = Column(String)

    role = Column(
        String,
        default=UserRole.USER
    )

    is_active = Column(
        Boolean,
        default=True
    )

    # User information
    address = Column(
        String,
        nullable=True
    )

    # Driver information
    license_number = Column(
        String,
        unique=True,
        nullable=True
    )

    license_expiry = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    must_change_password = Column(
        Boolean,
        default=False,
        nullable=False
    )
    # ---------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------

    # Bookings created by this user
    bookings = relationship(
        "Booking",
        foreign_keys="Booking.user_id",
        back_populates="user"
    )

    # Bookings assigned to this driver
    driver_bookings = relationship(
        "Booking",
        foreign_keys="Booking.driver_id",
        back_populates="driver"
    )
     # Ambulance currently assigned to this driver
    assigned_ambulance = relationship(
        "Ambulance",
        foreign_keys="Ambulance.current_driver_id",
        back_populates="current_driver",
        uselist=False
    )


# ============================================================================
# AMBULANCE MODEL
# ============================================================================

class Ambulance(Base):
    __tablename__ = "ambulances"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    registration_number = Column(
        String,
        unique=True,
        index=True
    )

    ambulance_type = Column(String)

    status = Column(
        String,
        default=AmbulanceStatus.AVAILABLE.value
    )

    current_driver_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # ---------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------

    bookings = relationship(
        "Booking",
        back_populates="ambulance"
    )

    current_driver = relationship(
        "User",
        foreign_keys=[current_driver_id],
        back_populates="assigned_ambulance"
    )

# ============================================================================
# BOOKING MODEL
# ============================================================================

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    user_id = Column(
        String,
        ForeignKey("users.id")
    )

    ambulance_id = Column(
        String,
        ForeignKey("ambulances.id"),
        nullable=True
    )

    driver_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=True
    )

    patient_name = Column(String)
    patient_phone = Column(String)

    pickup_address = Column(String)
    dropoff_address = Column(String)

    status = Column(
        String,
        default=BookingStatus.PENDING.value
    )

    booking_time = Column(
        DateTime,
        default=datetime.utcnow
    )

    assigned_time = Column(
        DateTime,
        nullable=True
    )

    completed_time = Column(
        DateTime,
        nullable=True
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="bookings"
    )

    driver = relationship(
        "User",
        foreign_keys=[driver_id],
        back_populates="driver_bookings"
    )

    ambulance = relationship(
        "Ambulance",
        back_populates="bookings"
    )
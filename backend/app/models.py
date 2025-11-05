"""Database models for the Inter-Paws scheduling platform."""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.extensions import db


class TimestampMixin:
    """Mixin providing timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Clinic(db.Model, TimestampMixin):
    """Represents a veterinary clinic within the platform."""

    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))

    users: Mapped[list["User"]] = relationship("User", back_populates="clinic")
    pets: Mapped[list["Pet"]] = relationship("Pet", back_populates="clinic")
    doctors: Mapped[list["Doctor"]] = relationship("Doctor", back_populates="clinic")
    rooms: Mapped[list["Room"]] = relationship("Room", back_populates="clinic")
    constraints: Mapped[list["Constraint"]] = relationship(
        "Constraint", back_populates="clinic"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="clinic"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="clinic"
    )

    def __repr__(self) -> str:
        return f"<Clinic id={self.id} name={self.name!r}>"


class User(db.Model, TimestampMixin):
    """Application user including clinic staff and pet owners."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int | None] = mapped_column(ForeignKey("clinics.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="staff", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    clinic: Mapped[Clinic | None] = relationship("Clinic", back_populates="users")
    pets: Mapped[list["Pet"]] = relationship("Pet", back_populates="owner")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="owner", foreign_keys="Appointment.owner_id"
    )
    feedback_events: Mapped[list["FeedbackEvent"]] = relationship(
        "FeedbackEvent", back_populates="user"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class Pet(db.Model, TimestampMixin):
    """Represents an animal registered with the clinic."""

    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int | None] = mapped_column(ForeignKey("clinics.id"), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    species: Mapped[str] = mapped_column(String(100), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(100))
    sex: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    color: Mapped[str | None] = mapped_column(String(50))
    microchip_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    notes: Mapped[str | None] = mapped_column(Text)

    clinic: Mapped[Clinic | None] = relationship("Clinic", back_populates="pets")
    owner: Mapped[User | None] = relationship("User", back_populates="pets")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="pet"
    )

    def __repr__(self) -> str:
        return f"<Pet id={self.id} name={self.name!r}>"


class Doctor(db.Model, TimestampMixin):
    """Represents a veterinarian or practitioner."""

    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(255))
    license_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    biography: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    clinic: Mapped[Clinic] = relationship("Clinic", back_populates="doctors")
    user: Mapped[User | None] = relationship("User")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="doctor"
    )
    constraints: Mapped[list["Constraint"]] = relationship(
        "Constraint", back_populates="doctor"
    )
    schedules: Mapped[list["DoctorSchedule"]] = relationship(
        "DoctorSchedule",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} name={self.display_name!r}>"


class Room(db.Model, TimestampMixin):
    """Rooms within a clinic where appointments take place."""

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    room_type: Mapped[str | None] = mapped_column(String(100))
    capacity: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    clinic: Mapped[Clinic] = relationship("Clinic", back_populates="rooms")
    constraints: Mapped[list["Constraint"]] = relationship(
        "Constraint", back_populates="room"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="room"
    )
    schedules: Mapped[list["RoomSchedule"]] = relationship(
        "RoomSchedule",
        back_populates="room",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Room id={self.id} name={self.name!r}>"


class Constraint(db.Model, TimestampMixin):
    """Scheduling constraints for doctors or rooms."""

    __tablename__ = "constraints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    recurrence: Mapped[str | None] = mapped_column(String(255))
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    clinic: Mapped[Clinic] = relationship("Clinic", back_populates="constraints")
    doctor: Mapped[Doctor | None] = relationship("Doctor", back_populates="constraints")
    room: Mapped[Room | None] = relationship("Room", back_populates="constraints")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="constraint"
    )

    def __repr__(self) -> str:
        return f"<Constraint id={self.id} title={self.title!r}>"


class DoctorSchedule(db.Model, TimestampMixin):
    """Recurring availability or blackout windows for a doctor."""

    __tablename__ = "doctor_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(20), default="availability", nullable=False)
    weekday: Mapped[int | None] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    clinic: Mapped[Clinic] = relationship("Clinic")
    doctor: Mapped[Doctor] = relationship("Doctor", back_populates="schedules")

    def __repr__(self) -> str:
        return f"<DoctorSchedule id={self.id} doctor_id={self.doctor_id} kind={self.kind!r}>"


class RoomSchedule(db.Model, TimestampMixin):
    """Recurring availability or blackout windows for a room."""

    __tablename__ = "room_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(20), default="availability", nullable=False)
    weekday: Mapped[int | None] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    clinic: Mapped[Clinic] = relationship("Clinic")
    room: Mapped[Room] = relationship("Room", back_populates="schedules")

    def __repr__(self) -> str:
        return f"<RoomSchedule id={self.id} room_id={self.room_id} kind={self.kind!r}>"


class Appointment(db.Model, TimestampMixin):
    """An appointment between a pet, owner, and doctor."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    pet_id: Mapped[int | None] = mapped_column(ForeignKey("pets.id"))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    constraint_id: Mapped[int | None] = mapped_column(ForeignKey("constraints.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduled", nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    clinic: Mapped[Clinic] = relationship("Clinic", back_populates="appointments")
    pet: Mapped[Pet | None] = relationship("Pet", back_populates="appointments")
    owner: Mapped[User | None] = relationship(
        "User", back_populates="appointments", foreign_keys=[owner_id]
    )
    doctor: Mapped[Doctor | None] = relationship("Doctor", back_populates="appointments")
    room: Mapped[Room | None] = relationship("Room", back_populates="appointments")
    constraint: Mapped[Constraint | None] = relationship(
        "Constraint", back_populates="appointments"
    )
    feedback_events: Mapped[list["FeedbackEvent"]] = relationship(
        "FeedbackEvent", back_populates="appointment"
    )

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} status={self.status!r}>"


class FeedbackEvent(db.Model, TimestampMixin):
    """Feedback submitted after an appointment."""

    __tablename__ = "feedback_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int | None] = mapped_column(Integer)
    sentiment: Mapped[str | None] = mapped_column(String(50))
    comments: Mapped[str | None] = mapped_column(Text)
    suggestion_rank: Mapped[int | None] = mapped_column(Integer)
    suggestion_score: Mapped[float | None] = mapped_column(Float)
    suggestion_slot_id: Mapped[int | None] = mapped_column(Integer)
    suggestion_start_time: Mapped[datetime | None] = mapped_column(DateTime)
    suggestion_end_time: Mapped[datetime | None] = mapped_column(DateTime)
    suggestion_doctor_id: Mapped[int | None] = mapped_column(Integer)
    suggestion_room_id: Mapped[int | None] = mapped_column(Integer)

    appointment: Mapped[Appointment] = relationship(
        "Appointment", back_populates="feedback_events"
    )
    user: Mapped[User | None] = relationship("User", back_populates="feedback_events")

    def __repr__(self) -> str:
        return f"<FeedbackEvent id={self.id} rating={self.rating}>"


class AuditLog(db.Model):
    """Immutable log of significant user actions for compliance."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int | None] = mapped_column(ForeignKey("clinics.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[dict | None] = mapped_column(db.JSON)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str | None] = mapped_column(String(128))
    response_hash: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    clinic: Mapped[Clinic | None] = relationship("Clinic", back_populates="audit_logs")
    user: Mapped[User | None] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r}>"

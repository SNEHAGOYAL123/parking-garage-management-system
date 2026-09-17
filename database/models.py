from datetime import datetime

from .db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }


class Garage(db.Model):
    __tablename__ = "garages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    spots = db.relationship(
        "Spot",
        back_populates="garage",
        cascade="all, delete-orphan"
    )

    tickets = db.relationship(
        "Ticket",
        back_populates="garage"
    )

    settings = db.relationship(
        "GarageSettings",
        back_populates="garage",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "created_at": self.created_at.isoformat(),
        }


class Spot(db.Model):
    __tablename__ = "spots"

    id = db.Column(db.Integer, primary_key=True)

    garage_id = db.Column(
        db.Integer,
        db.ForeignKey("garages.id"),
        nullable=False,
        index=True
    )

    level = db.Column(db.String(50), nullable=False)
    spot_number = db.Column(db.String(50), nullable=False)

    # Allowed values:
    # compact, standard, ev
    spot_type = db.Column(db.String(20), nullable=False)

    # This is maintained together with the active ticket.
    occupied = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    garage = db.relationship(
        "Garage",
        back_populates="spots"
    )

    tickets = db.relationship(
        "Ticket",
        back_populates="spot"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "garage_id",
            "level",
            "spot_number",
            name="uq_garage_spot"
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "garage_id": self.garage_id,
            "level": self.level,
            "spot_number": self.spot_number,
            "spot_type": self.spot_type,
            "occupied": self.occupied,
        }


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)

    garage_id = db.Column(
        db.Integer,
        db.ForeignKey("garages.id"),
        nullable=False,
        index=True
    )

    spot_id = db.Column(
        db.Integer,
        db.ForeignKey("spots.id"),
        nullable=False,
        index=True
    )

    plate = db.Column(
        db.String(30),
        nullable=False,
        index=True
    )

    # Allowed values:
    # compact, standard, ev
    vehicle_type = db.Column(
        db.String(20),
        nullable=False
    )

    check_in = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    check_out = db.Column(
        db.DateTime,
        nullable=True
    )

    fee = db.Column(
        db.Float,
        nullable=True
    )

    # parked / checked_out
    status = db.Column(
        db.String(20),
        nullable=False,
        default="parked",
        index=True
    )

    garage = db.relationship(
        "Garage",
        back_populates="tickets"
    )

    spot = db.relationship(
        "Spot",
        back_populates="tickets"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "garage_id": self.garage_id,
            "spot_id": self.spot_id,
            "plate": self.plate,
            "vehicle_type": self.vehicle_type,
            "check_in": self.check_in.isoformat(),
            "check_out": (
                self.check_out.isoformat()
                if self.check_out
                else None
            ),
            "fee": self.fee,
            "status": self.status,
            "spot": self.spot.to_dict() if self.spot else None,
        }


class GarageSettings(db.Model):
    __tablename__ = "garage_settings"

    id = db.Column(db.Integer, primary_key=True)

    garage_id = db.Column(
        db.Integer,
        db.ForeignKey("garages.id"),
        nullable=False,
        unique=True
    )

    # Currency is kept configurable rather than hard-coded
    # into the business logic.
    currency = db.Column(
        db.String(10),
        nullable=False,
        default="INR"
    )

    first_hour_rate = db.Column(
        db.Float,
        nullable=False,
        default=50.0
    )

    additional_hour_rate = db.Column(
        db.Float,
        nullable=False,
        default=30.0
    )

    daily_cap = db.Column(
        db.Float,
        nullable=False,
        default=300.0
    )

    garage = db.relationship(
        "Garage",
        back_populates="settings"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "garage_id": self.garage_id,
            "currency": self.currency,
            "first_hour_rate": self.first_hour_rate,
            "additional_hour_rate": self.additional_hour_rate,
            "daily_cap": self.daily_cap,
        }


# -------------------------------------------------------------------
# Database-level protection
# -------------------------------------------------------------------
#
# SQLite supports partial indexes. These indexes make the database
# reject two active tickets for the same parking spot or same plate.
#
# The application will ALSO validate these rules before inserting.
# The database constraint provides an additional safety layer.
#
db.Index(
    "uq_active_ticket_spot",
    Ticket.spot_id,
    unique=True,
    sqlite_where=(Ticket.status == "parked"),
)

db.Index(
    "uq_active_ticket_plate",
    Ticket.plate,
    unique=True,
    sqlite_where=(Ticket.status == "parked"),
)
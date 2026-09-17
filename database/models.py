from datetime import datetime

from sqlalchemy import Index, text
from database.db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )


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


class Spot(db.Model):
    __tablename__ = "spots"

    id = db.Column(db.Integer, primary_key=True)
    garage_id = db.Column(
        db.Integer,
        db.ForeignKey("garages.id"),
        nullable=False,
        index=True
    )
    level = db.Column(db.Integer, nullable=False)
    spot_number = db.Column(db.String(50), nullable=False)
    spot_type = db.Column(db.String(20), nullable=False)
    occupied = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "garage_id",
            "spot_number",
            name="uq_garage_spot_number"
        ),
    )


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

    status = db.Column(
        db.String(20),
        nullable=False,
        default="parked",
        index=True
    )


# Same spot cannot have two active parking sessions
Index(
    "uq_active_ticket_spot",
    Ticket.spot_id,
    unique=True,
    sqlite_where=text("status = 'parked'")
)


# Same vehicle cannot have two active sessions
# in the same garage
Index(
    "uq_active_ticket_plate",
    Ticket.garage_id,
    Ticket.plate,
    unique=True,
    sqlite_where=text("status = 'parked'")
)


class GarageSettings(db.Model):
    __tablename__ = "garage_settings"

    id = db.Column(db.Integer, primary_key=True)

    garage_id = db.Column(
        db.Integer,
        db.ForeignKey("garages.id"),
        nullable=False,
        unique=True
    )

    currency = db.Column(
        db.String(10),
        default="INR",
        nullable=False
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


class RateCard(db.Model):
    """
    Cleaned parking rate card.
    One rate card per spot type for each garage.
    """

    __tablename__ = "rate_cards"

    id = db.Column(db.Integer, primary_key=True)

    garage_id = db.Column(
        db.Integer,
        db.ForeignKey("garages.id"),
        nullable=False,
        index=True
    )

    spot_type = db.Column(
        db.String(20),
        nullable=False
    )

    first_hour_rate = db.Column(
        db.Float,
        nullable=False
    )

    additional_hour_rate = db.Column(
        db.Float,
        nullable=False
    )

    daily_cap = db.Column(
        db.Float,
        nullable=False
    )

    source_text = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "garage_id",
            "spot_type",
            name="uq_rate_card_garage_spot_type"
        ),
    )
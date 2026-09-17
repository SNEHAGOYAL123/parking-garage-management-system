from flask import Flask, request
from flask_cors import CORS
from datetime import datetime
import math

from database.db import db, DATABASE_PATH


def create_app():
    app = Flask(__name__)

    # ---------------------------------------------------------
    # Application configuration
    # ---------------------------------------------------------
    app.config["SECRET_KEY"] = "change-this-in-production"

    # SQLite persistent database
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{DATABASE_PATH}"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ---------------------------------------------------------
    # Initialize extensions
    # ---------------------------------------------------------
    db.init_app(app)
    CORS(app)

    # Import models so SQLAlchemy knows about all tables.
    from database.models import (
        User,
        Garage,
        Spot,
        Ticket,
        GarageSettings,
    )

    # ---------------------------------------------------------
    # Create database tables
    # ---------------------------------------------------------
    with app.app_context():
        db.create_all()

    # ---------------------------------------------------------
    # Health API
    # ---------------------------------------------------------
    @app.get("/api/health")
    def health_check():
        return {
            "status": "ok",
            "service": "Parking Garage Management System"
        }

    # ---------------------------------------------------------
    # Check-in API
    # ---------------------------------------------------------
    @app.post("/api/check-in")
    def check_in():
        data = request.get_json(silent=True) or {}

        plate = str(data.get("plate", "")).strip().upper()
        vehicle_type = str(
            data.get("vehicle_type", "")
        ).strip().lower()

        garage_id = data.get("garage_id", 1)

        # Validate plate
        if not plate:
            return {
                "error": "Vehicle plate is required."
            }, 400

        # Validate vehicle type
        if vehicle_type not in ["compact", "standard", "ev"]:
            return {
                "error": (
                    "vehicle_type must be "
                    "compact, standard, or ev."
                )
            }, 400

        # Find garage
        garage = db.session.get(Garage, garage_id)

        if not garage:
            return {
                "error": "Garage not found."
            }, 404

        # Prevent duplicate active parking
        existing_ticket = Ticket.query.filter_by(
            garage_id=garage.id,
            plate=plate,
            status="parked"
        ).first()

        if existing_ticket:
            return {
                "error": "This vehicle is already parked.",
                "ticket_id": existing_ticket.id,
                "spot_id": existing_ticket.spot_id
            }, 409

        # Find a suitable free spot
        spot_query = Spot.query.filter_by(
            garage_id=garage.id,
            occupied=False
        )

        # EV vehicles can only use EV spots
        if vehicle_type == "ev":
            spot_query = spot_query.filter_by(
                spot_type="ev"
            )

        # Normal vehicles cannot use EV spots
        else:
            spot_query = spot_query.filter(
                Spot.spot_type != "ev"
            )

        # Select the first available suitable spot
        spot = spot_query.order_by(
            Spot.level.asc(),
            Spot.id.asc()
        ).first()

        # No suitable spot
        if not spot:
            return {
                "error": f"No available {vehicle_type} spot."
            }, 409

        # Create ticket
        ticket = Ticket(
            garage_id=garage.id,
            spot_id=spot.id,
            plate=plate,
            vehicle_type=vehicle_type,
            status="parked"
        )

        # Mark spot occupied
        spot.occupied = True

        db.session.add(ticket)
        db.session.commit()

        return {
            "message": "Vehicle checked in successfully.",
            "ticket": {
                "id": ticket.id,
                "plate": ticket.plate,
                "vehicle_type": ticket.vehicle_type,
                "spot_id": ticket.spot_id,
                "level": spot.level,
                "spot_number": spot.spot_number,
                "check_in": ticket.check_in.isoformat()
            }
        }, 201

    # ---------------------------------------------------------
    # Check-out API
    # ---------------------------------------------------------
    @app.post("/api/check-out")
    def check_out():
        data = request.get_json(silent=True) or {}

        plate = str(data.get("plate", "")).strip().upper()
        garage_id = data.get("garage_id", 1)

        # Validate plate
        if not plate:
            return {
                "error": "Vehicle plate is required."
            }, 400

        # Find active ticket
        ticket = Ticket.query.filter_by(
            garage_id=garage_id,
            plate=plate,
            status="parked"
        ).first()

        if not ticket:
            return {
                "error": "No active parking ticket found for this plate."
            }, 404

        # Get pricing settings
        settings = GarageSettings.query.filter_by(
            garage_id=garage_id
        ).first()

        if not settings:
            return {
                "error": "Garage pricing settings not found."
            }, 500

        # -----------------------------------------------------
        # Calculate parking duration
        # -----------------------------------------------------
        checkout_time = datetime.utcnow()

        duration_seconds = (
            checkout_time - ticket.check_in
        ).total_seconds()

        # Part-hours are rounded up.
        duration_hours = max(
            1,
            math.ceil(duration_seconds / 3600)
        )

        # -----------------------------------------------------
        # Calculate fee
        # -----------------------------------------------------
        if duration_hours <= 1:
            fee = settings.first_hour_rate
        else:
            fee = (
                settings.first_hour_rate
                + (
                    duration_hours - 1
                ) * settings.additional_hour_rate
            )

        # Apply daily cap
        fee = min(
            fee,
            settings.daily_cap
        )

        # -----------------------------------------------------
        # Update ticket
        # -----------------------------------------------------
        ticket.check_out = checkout_time
        ticket.fee = fee
        ticket.status = "checked_out"

        # -----------------------------------------------------
        # Free parking spot
        # -----------------------------------------------------
        spot = db.session.get(
            Spot,
            ticket.spot_id
        )

        if spot:
            spot.occupied = False

        db.session.commit()

        # -----------------------------------------------------
        # Checkout response
        # -----------------------------------------------------
        return {
            "message": "Vehicle checked out successfully.",
            "ticket": {
                "id": ticket.id,
                "plate": ticket.plate,
                "spot_id": ticket.spot_id,
                "check_in": ticket.check_in.isoformat(),
                "check_out": ticket.check_out.isoformat(),
                "duration_hours": duration_hours,
                "fee": ticket.fee,
                "currency": settings.currency,
                "status": ticket.status
            }
        }, 200

    return app


# -------------------------------------------------------------
# Application entry point
# -------------------------------------------------------------
app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )


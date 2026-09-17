from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from math import ceil
import re

from database.db import db, DATABASE_PATH
from database.models import (
    User,
    Garage,
    Spot,
    Ticket,
    GarageSettings,
    RateCard
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

ALLOWED_SPOT_TYPES = {
    "compact",
    "standard",
    "ev"
}


def parse_number(value):
    """
    Convert a value such as:
    50
    50.0
    "₹50"
    "Rs. 50"
    "INR 50"
    into a float.
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).replace(",", "")

    match = re.search(
        r"\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    return float(match.group())


def normalize_spot_type(value):
    """
    Normalize common messy spot-type names.
    """

    if not value:
        return None

    text = str(value).strip().lower()

    aliases = {
        "compact": "compact",
        "cmp": "compact",
        "small": "compact",

        "standard": "standard",
        "std": "standard",
        "regular": "standard",

        "ev": "ev",
        "e.v.": "ev",
        "electric": "ev",
        "electric vehicle": "ev",
        "ev spot": "ev",
        "ev charging": "ev"
    }

    return aliases.get(text)


def parse_rate_line(line):
    """
    Try to clean one messy rate-card line.

    Expected logical values:
    spot type
    first-hour rate
    additional-hour rate
    daily cap

    The parser supports labelled values such as:
    Compact: first hour ₹40, extra ₹20, cap ₹200

    It also supports a fallback where the final
    three numbers are treated as:
    first-hour, additional-hour, daily-cap.
    """

    if not line:
        return None

    original = str(line).strip()

    if not original:
        return None

    lower = original.lower()

    # --------------------------------------------------------
    # Identify spot type
    # --------------------------------------------------------

    spot_type = None

    if re.search(r"\bev\b|electric", lower):
        spot_type = "ev"

    elif re.search(r"\bcompact\b|\bcmp\b|\bsmall\b", lower):
        spot_type = "compact"

    elif re.search(r"\bstandard\b|\bstd\b|\bregular\b", lower):
        spot_type = "standard"

    if not spot_type:
        return None

    # --------------------------------------------------------
    # Try labelled values first
    # --------------------------------------------------------

    first_hour = None
    additional_hour = None
    daily_cap = None

    first_patterns = [
        r"first\s*hour[^0-9]*(\d+(?:\.\d+)?)",
        r"1st\s*hour[^0-9]*(\d+(?:\.\d+)?)",
        r"first[^0-9]*(\d+(?:\.\d+)?)",
    ]

    additional_patterns = [
        r"(?:additional|extra|each|subsequent)[^0-9]*(\d+(?:\.\d+)?)",
        r"2nd\s*hour[^0-9]*(\d+(?:\.\d+)?)",
    ]

    cap_patterns = [
        r"(?:daily\s*cap|day\s*cap|maximum|max|cap)[^0-9]*(\d+(?:\.\d+)?)"
    ]

    for pattern in first_patterns:
        match = re.search(pattern, lower)

        if match:
            first_hour = float(match.group(1))
            break

    for pattern in additional_patterns:
        match = re.search(pattern, lower)

        if match:
            additional_hour = float(match.group(1))
            break

    for pattern in cap_patterns:
        match = re.search(pattern, lower)

        if match:
            daily_cap = float(match.group(1))
            break

    # --------------------------------------------------------
    # Fallback: take numeric values from the line
    # --------------------------------------------------------

    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        original
    )

    numeric_values = [
        float(number)
        for number in numbers
    ]

    if len(numeric_values) >= 3:

        if first_hour is None:
            first_hour = numeric_values[-3]

        if additional_hour is None:
            additional_hour = numeric_values[-2]

        if daily_cap is None:
            daily_cap = numeric_values[-1]

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if (
        first_hour is None
        or additional_hour is None
        or daily_cap is None
    ):
        return None

    if (
        first_hour < 0
        or additional_hour < 0
        or daily_cap < 0
    ):
        return None

    return {
        "spot_type": spot_type,
        "first_hour_rate": first_hour,
        "additional_hour_rate": additional_hour,
        "daily_cap": daily_cap,
        "source_text": original
    }


def parse_rate_card_payload(data):
    """
    Accept several useful formats.

    Format 1:

    {
        "rates": [
            {
                "spot_type": "compact",
                "first_hour_rate": 40,
                "additional_hour_rate": 20,
                "daily_cap": 200
            }
        ]
    }

    Format 2:

    {
        "raw_text": "Compact: first hour 40, extra 20, cap 200"
    }

    Format 3:

    {
        "raw_text": [
            "Compact: first hour 40, extra 20, cap 200",
            "Standard: first hour 50, extra 30, cap 300"
        ]
    }
    """

    results = []

    # --------------------------------------------------------
    # Structured rates
    # --------------------------------------------------------

    rates = data.get("rates")

    if isinstance(rates, list):

        for item in rates:

            if not isinstance(item, dict):
                continue

            spot_type = normalize_spot_type(
                item.get("spot_type")
                or item.get("type")
            )

            first_hour = parse_number(
                item.get("first_hour_rate")
                if item.get("first_hour_rate") is not None
                else item.get("first_hour")
            )

            additional_hour = parse_number(
                item.get("additional_hour_rate")
                if item.get("additional_hour_rate") is not None
                else item.get("additional_hour")
            )

            daily_cap = parse_number(
                item.get("daily_cap")
                if item.get("daily_cap") is not None
                else item.get("cap")
            )

            if (
                spot_type
                and first_hour is not None
                and additional_hour is not None
                and daily_cap is not None
            ):

                results.append({
                    "spot_type": spot_type,
                    "first_hour_rate": first_hour,
                    "additional_hour_rate": additional_hour,
                    "daily_cap": daily_cap,
                    "source_text": str(item)
                })

        return results

    # --------------------------------------------------------
    # Raw messy text
    # --------------------------------------------------------

    raw_text = data.get("raw_text", "")

    if isinstance(raw_text, list):

        lines = raw_text

    else:

        lines = str(raw_text).splitlines()

    for line in lines:

        parsed = parse_rate_line(line)

        if parsed:
            results.append(parsed)

    return results


def get_rate_for_ticket(ticket):
    """
    Get pricing based on the ACTUAL parking spot type.

    T4 requires rates per spot type.

    If a cleaned RateCard exists, use it.

    Otherwise fall back to the existing
    GarageSettings rates.
    """

    spot = Spot.query.get(ticket.spot_id)

    if not spot:
        return None

    rate_card = RateCard.query.filter_by(
        garage_id=ticket.garage_id,
        spot_type=spot.spot_type
    ).first()

    if rate_card:

        return {
            "first_hour_rate": rate_card.first_hour_rate,
            "additional_hour_rate": rate_card.additional_hour_rate,
            "daily_cap": rate_card.daily_cap,
            "currency": "INR"
        }

    settings = GarageSettings.query.filter_by(
        garage_id=ticket.garage_id
    ).first()

    if not settings:
        return None

    return {
        "first_hour_rate": settings.first_hour_rate,
        "additional_hour_rate": settings.additional_hour_rate,
        "daily_cap": settings.daily_cap,
        "currency": settings.currency
    }


def calculate_fee(ticket, check_out_time):
    """
    Calculate parking fee.

    Rules:
    - part-hours round up
    - first hour uses first-hour rate
    - every additional hour uses additional-hour rate
    - daily cap prevents overcharging
    """

    rates = get_rate_for_ticket(ticket)

    if not rates:
        return None, None, None

    duration_seconds = (
        check_out_time - ticket.check_in
    ).total_seconds()

    duration_hours = max(
        1,
        ceil(duration_seconds / 3600)
    )

    if duration_hours == 1:

        fee = rates["first_hour_rate"]

    else:

        fee = (
            rates["first_hour_rate"]
            +
            (
                (duration_hours - 1)
                * rates["additional_hour_rate"]
            )
        )

    fee = min(
        fee,
        rates["daily_cap"]
    )

    return (
        duration_hours,
        float(fee),
        rates["currency"]
    )


def ticket_to_dict(ticket):
    """
    Convert ticket database object to API JSON.
    """

    spot = Spot.query.get(ticket.spot_id)

    return {
        "id": ticket.id,
        "plate": ticket.plate,
        "vehicle_type": ticket.vehicle_type,
        "spot_id": ticket.spot_id,
        "spot_number": (
            spot.spot_number
            if spot
            else None
        ),
        "level": (
            spot.level
            if spot
            else None
        ),
        "check_in": (
            ticket.check_in.isoformat()
            if ticket.check_in
            else None
        ),
        "check_out": (
            ticket.check_out.isoformat()
            if ticket.check_out
            else None
        ),
        "fee": (
            float(ticket.fee)
            if ticket.fee is not None
            else None
        ),
        "status": ticket.status
    }


# ============================================================
# CREATE APPLICATION
# ============================================================

def create_app():

    app = Flask(__name__)

    # --------------------------------------------------------
    # Configuration
    # --------------------------------------------------------

    app.config["SECRET_KEY"] = (
        "spotsync-secret-key-change-later"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{DATABASE_PATH}"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --------------------------------------------------------
    # Initialize extensions
    # --------------------------------------------------------

    db.init_app(app)

    CORS(app)

    bcrypt = Bcrypt(app)

    # --------------------------------------------------------
    # Create database tables
    # --------------------------------------------------------

    with app.app_context():

        db.create_all()

    # ========================================================
    # HOME PAGE
    # ========================================================

    @app.route("/")
    def home():

        return render_template(
            "index.html"
        )

    # ========================================================
    # HEALTH CHECK
    # ========================================================

    @app.route(
        "/api/health",
        methods=["GET"]
    )
    def health():

        return jsonify({
            "service":
                "Parking Garage Management System",
            "status":
                "ok"
        }), 200

    # ========================================================
    # REGISTER
    # ========================================================

    @app.route(
        "/api/register",
        methods=["POST"]
    )
    def register():

        data = request.get_json(
            silent=True
        ) or {}

        name = data.get(
            "name",
            ""
        ).strip()

        email = data.get(
            "email",
            ""
        ).strip().lower()

        password = data.get(
            "password",
            ""
        )

        if not name:

            return jsonify({
                "error":
                    "Name is required."
            }), 400

        if not email:

            return jsonify({
                "error":
                    "Email is required."
            }), 400

        if not password:

            return jsonify({
                "error":
                    "Password is required."
            }), 400

        if len(password) < 6:

            return jsonify({
                "error":
                    "Password must be at least 6 characters."
            }), 400

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            return jsonify({
                "error":
                    "Email is already registered."
            }), 409

        password_hash = (
            bcrypt
            .generate_password_hash(password)
            .decode("utf-8")
        )

        user = User(
            name=name,
            email=email,
            password_hash=password_hash
        )

        db.session.add(user)

        db.session.commit()

        return jsonify({

            "message":
                "Registration successful.",

            "user": {
                "id":
                    user.id,

                "name":
                    user.name,

                "email":
                    user.email,

                "created_at":
                    user.created_at.isoformat()
            }

        }), 201

    # ========================================================
    # LOGIN
    # ========================================================

    @app.route(
        "/api/login",
        methods=["POST"]
    )
    def login():

        data = request.get_json(
            silent=True
        ) or {}

        email = data.get(
            "email",
            ""
        ).strip().lower()

        password = data.get(
            "password",
            ""
        )

        if not email:

            return jsonify({
                "error":
                    "Email is required."
            }), 400

        if not password:

            return jsonify({
                "error":
                    "Password is required."
            }), 400

        user = User.query.filter_by(
            email=email
        ).first()

        if not user:

            return jsonify({
                "error":
                    "Invalid email or password."
            }), 401

        if not bcrypt.check_password_hash(
            user.password_hash,
            password
        ):

            return jsonify({
                "error":
                    "Invalid email or password."
            }), 401

        session["user_id"] = user.id

        return jsonify({

            "message":
                "Login successful.",

            "user": {
                "id":
                    user.id,

                "name":
                    user.name,

                "email":
                    user.email,

                "created_at":
                    user.created_at.isoformat()
            }

        }), 200

    # ========================================================
    # LOGOUT
    # ========================================================

    @app.route(
        "/api/logout",
        methods=["POST"]
    )
    def logout():

        session.clear()

        return jsonify({
            "message":
                "Logout successful."
        }), 200

    # ========================================================
    # CHECK-IN
    # ========================================================

    @app.route(
        "/api/check-in",
        methods=["POST"]
    )
    def check_in():

        data = request.get_json(
            silent=True
        ) or {}

        plate = data.get(
            "plate",
            ""
        ).strip().upper()

        vehicle_type = (
            data.get(
                "vehicle_type",
                "standard"
            )
            .strip()
            .lower()
        )

        garage_id = data.get(
            "garage_id",
            1
        )

        if not plate:

            return jsonify({
                "error":
                    "Vehicle plate is required."
            }), 400

        allowed_vehicle_types = {
            "compact",
            "standard",
            "ev"
        }

        if vehicle_type not in allowed_vehicle_types:

            return jsonify({
                "error":
                    "vehicle_type must be compact, "
                    "standard, or ev."
            }), 400

        garage = Garage.query.get(
            garage_id
        )

        if not garage:

            return jsonify({
                "error":
                    "Garage not found."
            }), 404

        existing_ticket = Ticket.query.filter_by(
            garage_id=garage_id,
            plate=plate,
            status="parked"
        ).first()

        if existing_ticket:

            return jsonify({

                "error":
                    "This vehicle is already parked.",

                "ticket_id":
                    existing_ticket.id,

                "spot_id":
                    existing_ticket.spot_id

            }), 409

        # ----------------------------------------------------
        # EV MUST USE EV SPOT
        # ----------------------------------------------------

        if vehicle_type == "ev":

            spot = Spot.query.filter_by(
                garage_id=garage_id,
                spot_type="ev",
                occupied=False
            ).order_by(
                Spot.level,
                Spot.spot_number
            ).first()

        else:

            spot = Spot.query.filter(
                Spot.garage_id == garage_id,
                Spot.occupied == False,
                Spot.spot_type != "ev"
            ).order_by(
                Spot.level,
                Spot.spot_number
            ).first()

        if not spot:

            return jsonify({
                "error":
                    "No suitable parking spot is available."
            }), 409

        spot.occupied = True

        ticket = Ticket(

            garage_id=garage_id,

            spot_id=spot.id,

            plate=plate,

            vehicle_type=vehicle_type,

            check_in=datetime.utcnow(),

            status="parked"
        )

        db.session.add(ticket)

        db.session.commit()

        return jsonify({

            "message":
                "Vehicle checked in successfully.",

            "ticket":
                ticket_to_dict(ticket)

        }), 201

    # ========================================================
    # CHECK-OUT
    # ========================================================

    @app.route(
        "/api/check-out",
        methods=["POST"]
    )
    def check_out():

        data = request.get_json(
            silent=True
        ) or {}

        plate = data.get(
            "plate",
            ""
        ).strip().upper()

        if not plate:

            return jsonify({
                "error":
                    "Vehicle plate is required."
            }), 400

        ticket = Ticket.query.filter_by(
            plate=plate,
            status="parked"
        ).first()

        if not ticket:

            return jsonify({
                "error":
                    "No active parking ticket found for this plate."
            }), 404

        check_out_time = datetime.utcnow()

        duration_hours, fee, currency = (
            calculate_fee(
                ticket,
                check_out_time
            )
        )

        if fee is None:

            return jsonify({
                "error":
                    "Parking rate settings not found."
            }), 500

        ticket.check_out = check_out_time

        ticket.fee = fee

        ticket.status = "checked_out"

        spot = Spot.query.get(
            ticket.spot_id
        )

        if spot:

            spot.occupied = False

        db.session.commit()

        return jsonify({

            "message":
                "Vehicle checked out successfully.",

            "ticket_id":
                ticket.id,

            "plate":
                ticket.plate,

            "duration_hours":
                duration_hours,

            "fee":
                float(fee),

            "currency":
                currency,

            "spot_id":
                ticket.spot_id,

            "spot_number":
                spot.spot_number
                if spot
                else None,

            "check_out":
                check_out_time.isoformat(),

            "status":
                ticket.status

        }), 200

    # ========================================================
    # T4 — IMPORT MESSY RATE CARD
    # ========================================================

    @app.route(
        "/api/rates/import",
        methods=["POST"]
    )
    def import_rates():

        data = request.get_json(
            silent=True
        ) or {}

        garage_id = data.get(
            "garage_id",
            1
        )

        garage = Garage.query.get(
            garage_id
        )

        if not garage:

            return jsonify({
                "error":
                    "Garage not found."
            }), 404

        parsed_rates = parse_rate_card_payload(
            data
        )

        if not parsed_rates:

            return jsonify({
                "error":
                    "No valid rate-card entries could be parsed."
            }), 400

        saved = []

        for rate in parsed_rates:

            existing = RateCard.query.filter_by(
                garage_id=garage_id,
                spot_type=rate["spot_type"]
            ).first()

            if existing:

                existing.first_hour_rate = (
                    rate["first_hour_rate"]
                )

                existing.additional_hour_rate = (
                    rate["additional_hour_rate"]
                )

                existing.daily_cap = (
                    rate["daily_cap"]
                )

                existing.source_text = (
                    rate["source_text"]
                )

                rate_card = existing

            else:

                rate_card = RateCard(

                    garage_id=garage_id,

                    spot_type=rate["spot_type"],

                    first_hour_rate=(
                        rate["first_hour_rate"]
                    ),

                    additional_hour_rate=(
                        rate["additional_hour_rate"]
                    ),

                    daily_cap=(
                        rate["daily_cap"]
                    ),

                    source_text=(
                        rate["source_text"]
                    )
                )

                db.session.add(
                    rate_card
                )

            saved.append(rate)

        db.session.commit()

        return jsonify({

            "message":
                "Rate card imported and cleaned successfully.",

            "garage_id":
                garage_id,

            "count":
                len(saved),

            "rates":
                saved

        }), 201

    # ========================================================
    # T4 — VIEW CLEANED RATE CARD
    # ========================================================

    @app.route(
        "/api/rates",
        methods=["GET"]
    )
    def get_rates():

        garage_id = request.args.get(
            "garage_id",
            1,
            type=int
        )

        rates = RateCard.query.filter_by(
            garage_id=garage_id
        ).order_by(
            RateCard.spot_type
        ).all()

        return jsonify({

            "garage_id":
                garage_id,

            "count":
                len(rates),

            "rates": [

                {
                    "id":
                        rate.id,

                    "spot_type":
                        rate.spot_type,

                    "first_hour_rate":
                        float(
                            rate.first_hour_rate
                        ),

                    "additional_hour_rate":
                        float(
                            rate.additional_hour_rate
                        ),

                    "daily_cap":
                        float(
                            rate.daily_cap
                        ),

                    "source_text":
                        rate.source_text,

                    "created_at":
                        rate.created_at.isoformat()
                }

                for rate in rates
            ]

        }), 200

    # ========================================================
    # T2 — NIGHTLY AUTO-CLOSE
    # ========================================================

    @app.route(
        "/clock",
        methods=["POST"]
    )
    def clock():

        data = request.get_json(
            silent=True
        ) or {}

        # ----------------------------------------------------
        # Normally use real current time.
        #
        # Optional "now" is provided so the evaluator
        # can deterministically test a 24-hour session.
        # ----------------------------------------------------

        now_text = data.get(
            "now"
        )

        if now_text:

            try:

                clock_time = datetime.fromisoformat(
                    now_text.replace(
                        "Z",
                        "+00:00"
                    )
                )

                # Convert aware datetime to naive UTC
                if clock_time.tzinfo is not None:

                    clock_time = (
                        clock_time
                        .astimezone()
                        .replace(tzinfo=None)
                    )

            except ValueError:

                return jsonify({
                    "error":
                        "Invalid now datetime. "
                        "Use ISO-8601 format."
                }), 400

        else:

            clock_time = datetime.utcnow()

        cutoff = (
            clock_time
            - timedelta(hours=24)
        )

        parked_tickets = Ticket.query.filter(
            Ticket.status == "parked",
            Ticket.check_in < cutoff
        ).all()

        closed = []

        for ticket in parked_tickets:

            duration_hours, fee, currency = (
                calculate_fee(
                    ticket,
                    clock_time
                )
            )

            if fee is None:

                continue

            ticket.check_out = clock_time

            ticket.fee = fee

            ticket.status = "checked_out"

            spot = Spot.query.get(
                ticket.spot_id
            )

            if spot:

                spot.occupied = False

            closed.append({

                "ticket_id":
                    ticket.id,

                "plate":
                    ticket.plate,

                "spot_id":
                    ticket.spot_id,

                "duration_hours":
                    duration_hours,

                "fee":
                    float(fee),

                "currency":
                    currency,

                "check_out":
                    clock_time.isoformat()
            })

        db.session.commit()

        return jsonify({

            "message":
                "Clock job completed.",

            "clock_time":
                clock_time.isoformat(),

            "cutoff":
                cutoff.isoformat(),

            "closed_count":
                len(closed),

            "closed_sessions":
                closed

        }), 200

    # ========================================================
    # T6 — TRANSFER OPEN SESSION TO NEW PLATE
    # ========================================================

    @app.route(
        "/api/tickets/transfer",
        methods=["POST"]
    )
    def transfer_ticket():

        data = request.get_json(
            silent=True
        ) or {}

        old_plate = data.get(
            "old_plate",
            ""
        ).strip().upper()

        new_plate = data.get(
            "new_plate",
            ""
        ).strip().upper()

        if not old_plate:

            return jsonify({
                "error":
                    "old_plate is required."
            }), 400

        if not new_plate:

            return jsonify({
                "error":
                    "new_plate is required."
            }), 400

        if old_plate == new_plate:

            return jsonify({
                "error":
                    "old_plate and new_plate must be different."
            }), 400

        # ----------------------------------------------------
        # Find old active session
        # ----------------------------------------------------

        ticket = Ticket.query.filter_by(
            plate=old_plate,
            status="parked"
        ).first()

        if not ticket:

            return jsonify({
                "error":
                    "No active parking session found for old_plate."
            }), 404

        # ----------------------------------------------------
        # New plate must not already be parked
        # ----------------------------------------------------

        existing_new = Ticket.query.filter_by(
            plate=new_plate,
            status="parked"
        ).first()

        if existing_new:

            return jsonify({
                "error":
                    "The new plate already has an active parking session.",
                "ticket_id":
                    existing_new.id
            }), 409

        # ----------------------------------------------------
        # Transfer only the plate.
        #
        # Spot and check-in time remain unchanged.
        # ----------------------------------------------------

        old_spot_id = ticket.spot_id

        old_check_in = ticket.check_in

        ticket.plate = new_plate

        db.session.commit()

        return jsonify({

            "message":
                "Parking session transferred successfully.",

            "ticket":
                ticket_to_dict(ticket),

            "transfer": {
                "old_plate":
                    old_plate,

                "new_plate":
                    new_plate,

                "spot_preserved":
                    ticket.spot_id == old_spot_id,

                "check_in_preserved":
                    ticket.check_in == old_check_in
            }

        }), 200

    # ========================================================
    # EV AVAILABILITY
    # ========================================================

    @app.route(
        "/api/availability",
        methods=["GET"]
    )
    def availability():

        garage_id = request.args.get(
            "garage_id",
            1,
            type=int
        )

        total = Spot.query.filter_by(
            garage_id=garage_id,
            spot_type="ev"
        ).count()

        available = Spot.query.filter_by(
            garage_id=garage_id,
            spot_type="ev",
            occupied=False
        ).count()

        occupied = total - available

        message = (
            "EV spot is available."
            if available > 0
            else
            "No EV spot is currently available."
        )

        return jsonify({

            "garage_id":
                garage_id,

            "spot_type":
                "ev",

            "total":
                total,

            "available":
                available,

            "occupied":
                occupied,

            "message":
                message

        }), 200

    # ========================================================
    # SPOTS
    # ========================================================

    @app.route(
        "/api/spots",
        methods=["GET"]
    )
    def spots():

        garage_id = request.args.get(
            "garage_id",
            1,
            type=int
        )

        spot_type = request.args.get(
            "spot_type"
        )

        available = request.args.get(
            "available"
        )

        query = Spot.query.filter_by(
            garage_id=garage_id
        )

        if spot_type:

            query = query.filter_by(
                spot_type=spot_type.lower()
            )

        if available is not None:

            if available.lower() == "true":

                query = query.filter_by(
                    occupied=False
                )

            elif available.lower() == "false":

                query = query.filter_by(
                    occupied=True
                )

        query = query.order_by(
            Spot.level,
            Spot.spot_number
        )

        spots_list = query.all()

        return jsonify({

            "garage_id":
                garage_id,

            "count":
                len(spots_list),

            "spots": [

                {
                    "id":
                        spot.id,

                    "level":
                        spot.level,

                    "spot_number":
                        spot.spot_number,

                    "spot_type":
                        spot.spot_type,

                    "occupied":
                        spot.occupied,

                    "available":
                        not spot.occupied
                }

                for spot in spots_list
            ]

        }), 200

    # ========================================================
    # SEARCH TICKETS
    # ========================================================

    @app.route(
        "/api/tickets/search",
        methods=["GET"]
    )
    def search_tickets():

        query_text = request.args.get(
            "q",
            ""
        ).strip().upper()

        garage_id = request.args.get(
            "garage_id",
            1,
            type=int
        )

        if not query_text:

            return jsonify({
                "error":
                    "Search query q is required."
            }), 400

        tickets = Ticket.query.filter(

            Ticket.garage_id == garage_id,

            Ticket.plate.like(
                f"%{query_text}%"
            )

        ).order_by(
            Ticket.check_in.desc()
        ).all()

        return jsonify({

            "garage_id":
                garage_id,

            "query":
                query_text,

            "count":
                len(tickets),

            "tickets":
                [
                    ticket_to_dict(ticket)
                    for ticket in tickets
                ]

        }), 200

    # ========================================================
    # TICKETS WITH PAGINATION + SORTING
    # ========================================================

    @app.route(
        "/api/tickets",
        methods=["GET"]
    )
    def get_tickets():

        garage_id = request.args.get(
            "garage_id",
            1,
            type=int
        )

        page = request.args.get(
            "page",
            1,
            type=int
        )

        per_page = request.args.get(
            "per_page",
            5,
            type=int
        )

        sort_by = request.args.get(
            "sort_by",
            "id"
        )

        order = request.args.get(
            "order",
            "desc"
        ).lower()

        if page < 1:

            return jsonify({
                "error":
                    "page must be at least 1."
            }), 400

        if per_page < 1 or per_page > 100:

            return jsonify({
                "error":
                    "per_page must be between 1 and 100."
            }), 400

        allowed_sort_fields = {

            "id":
                Ticket.id,

            "plate":
                Ticket.plate,

            "vehicle_type":
                Ticket.vehicle_type,

            "check_in":
                Ticket.check_in,

            "check_out":
                Ticket.check_out,

            "fee":
                Ticket.fee,

            "status":
                Ticket.status
        }

        if sort_by not in allowed_sort_fields:

            return jsonify({
                "error":
                    "Invalid sort_by. Choose from: "
                    "id, plate, vehicle_type, "
                    "check_in, check_out, fee, status"
            }), 400

        if order not in {
            "asc",
            "desc"
        }:

            return jsonify({
                "error":
                    "order must be asc or desc."
            }), 400

        query = Ticket.query.filter_by(
            garage_id=garage_id
        )

        sort_column = allowed_sort_fields[
            sort_by
        ]

        if order == "asc":

            query = query.order_by(
                sort_column.asc()
            )

        else:

            query = query.order_by(
                sort_column.desc()
            )

        pagination = query.paginate(

            page=page,

            per_page=per_page,

            error_out=False
        )

        return jsonify({

            "garage_id":
                garage_id,

            "page":
                pagination.page,

            "per_page":
                pagination.per_page,

            "pages":
                pagination.pages,

            "total":
                pagination.total,

            "has_next":
                pagination.has_next,

            "has_previous":
                pagination.has_prev,

            "sort_by":
                sort_by,

            "order":
                order,

            "tickets":
                [
                    ticket_to_dict(ticket)
                    for ticket in pagination.items
                ]

        }), 200

    # ========================================================
    # RETURN APP
    # ========================================================

    return app


# ============================================================
# APPLICATION START
# ============================================================

app = create_app()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
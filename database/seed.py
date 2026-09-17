from app import create_app
from database.db import db
from database.models import Garage, Spot, GarageSettings


app = create_app()

with app.app_context():
    # Check if garage already exists
    garage = Garage.query.first()

    if garage:
        print("Garage already exists.")
        print(f"Garage ID: {garage.id}")
        print(f"Total spots: {Spot.query.filter_by(garage_id=garage.id).count()}")
    else:
        # Create garage
        garage = Garage(
            name="City Centre Parking Garage",
            address="City Centre"
        )
        db.session.add(garage)
        db.session.flush()

        # Create garage settings
        settings = GarageSettings(
            garage_id=garage.id,
            currency="INR",
            first_hour_rate=50,
            additional_hour_rate=30,
            daily_cap=300
        )
        db.session.add(settings)

        # Create parking spots
        spot_types = {
            "compact": 6,
            "standard": 12,
            "ev": 6
        }

        for level in range(1, 4):
            for spot_type, count in spot_types.items():
                for number in range(1, count + 1):
                    spot = Spot(
                        garage_id=garage.id,
                        level=level,
                        spot_number=f"L{level}-{spot_type.upper()}-{number}",
                        spot_type=spot_type,
                        occupied=False
                    )
                    db.session.add(spot)

        db.session.commit()

        total_spots = Spot.query.filter_by(
            garage_id=garage.id
        ).count()

        print("Initial garage data created successfully.")
        print(f"Garage ID: {garage.id}")
        print(f"Total spots: {total_spots}")
# parking-garage-management-system

# SpotSync – Parking Garage Management System

SpotSync is a Flask-based Parking Garage Management System designed to manage parking spots, vehicle entry and exit, parking availability, parking tickets, rate cards, and automated parking operations.

## Features

* User registration and login
* Secure password handling
* Vehicle check-in
* Vehicle check-out with fee calculation
* Parking spot availability
* EV parking spot availability
* Search parking tickets
* Ticket pagination and sorting
* Parking rate card import and cleaning
* Automated 24-hour session closure and billing
* Parking session transfer to another vehicle plate
* Responsive web dashboard

## Technology Stack

* **Backend:** Python, Flask
* **Database:** SQLite, SQLAlchemy
* **Frontend:** HTML, CSS, JavaScript, Bootstrap
* **API:** REST APIs

## Project Structure

```text
parking-garage-management-system/
│
├── app.py
├── database/
│   └── models.py
├── templates/
│   └── index.html
├── static/
│   ├── app.js
│   └── style.css
├── AI_LOGS.md
├── REASONING.md
├── .gitignore
└── README.md
```

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/SNEHAGOYAL123/parking-garage-management-system.git
cd parking-garage-management-system
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

Activate it:

**Linux / GitHub Codespaces:**

```bash
source .venv/bin/activate
```

**Windows:**

```bash
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

The application runs on:

```text
http://127.0.0.1:5000
```

## Main API Endpoints

| Endpoint                  | Purpose                               |
| ------------------------- | ------------------------------------- |
| `GET /api/health`         | Check application health              |
| `POST /api/register`      | Register a new user                   |
| `POST /api/login`         | Login user                            |
| `POST /api/logout`        | Logout user                           |
| `POST /api/check-in`      | Check in a vehicle                    |
| `POST /api/check-out`     | Check out a vehicle                   |
| `GET /api/availability`   | Check parking availability            |
| `GET /api/spots`          | Get parking spots                     |
| `GET /api/tickets`        | Get parking records                   |
| `GET /api/tickets/search` | Search parking tickets                |
| `POST /clock`             | Run automated parking session closure |

## Assessment Scenarios

### T4 – Rate Card Import

The system supports importing a rate card containing parking rates for different spot types.

The imported data is cleaned and stored with:

* First-hour rate
* Additional-hour rate
* Daily cap
* Spot type
* Original source text

### T2 – Automated 24-Hour Closure and Billing

The clock job identifies parking sessions that have exceeded 24 hours.

The system automatically:

1. Identifies overdue parking sessions.
2. Closes the parking session.
3. Calculates the applicable parking fee.
4. Updates the ticket with checkout time and fee.
5. Releases the parking spot.

### T6 – Parking Session Transfer

An active parking session can be transferred from one vehicle plate to another.

During the transfer:

* The new vehicle plate is stored.
* The original parking spot is preserved.
* The original check-in time is preserved.
* The active parking session remains open.

This supports a valet hand-off workflow.

## Web Dashboard

The web interface provides:

* Login and registration
* Parking dashboard
* Parking statistics
* Vehicle check-in
* Vehicle check-out
* Parking ticket search
* Spot type filtering
* Availability filtering
* Ticket sorting
* Parking records

## Security and Repository Hygiene

The repository excludes sensitive or unnecessary local files such as:

* Virtual environment files
* Python cache files
* Local database files
* Cookie/session files

These files are excluded through `.gitignore`.

## Documentation

* `README.md` – Project overview and setup instructions
* `AI_LOGS.md` – AI-assisted development logs
* `REASONING.md` – Development reasoning and implementation notes

## Author

**Sneha Goyal**

B.Tech Artificial Intelligence
Swami Keshwanand Institute of Technology (SKIT), Jaipur

## Repository

GitHub: https://github.com/SNEHAGOYAL123/parking-garage-management-system

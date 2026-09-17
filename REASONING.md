# SpotSync – Development Reasoning

## 1. Problem Understanding

The task was to build a Parking Garage Management System that allows users to manage parking operations through a web interface and APIs.

The main workflow includes:

1. User registration and login.
2. Vehicle check-in.
3. Parking spot allocation.
4. Parking availability tracking.
5. Vehicle check-out.
6. Parking fee calculation.
7. Parking ticket search and listing.
8. Parking rate management.
9. Automated handling of long-running parking sessions.
10. Transfer of an active parking session to another vehicle plate.

The implementation was designed around the existing Flask application and database structure while adding the required functionality.

---

## 2. Technology Decision

### Backend

Flask was used because the application is API-driven and requires a lightweight Python web framework.

### Database

SQLite with SQLAlchemy was used for storing:

* Users
* Garages
* Parking spots
* Parking tickets
* Garage settings
* Parking rates

SQLAlchemy provides a structured way to work with the database through Python models.

### Frontend

The frontend uses:

* HTML
* CSS
* JavaScript
* Bootstrap

JavaScript communicates with the Flask backend using API requests.

---

## 3. Authentication

The system provides registration and login functionality.

For registration:

1. Validate the submitted user information.
2. Check whether the email already exists.
3. Hash the password.
4. Store the user in the database.

For login:

1. Find the user by email.
2. Verify the password.
3. Create a session for the authenticated user.

Logout clears the active session.

---

## 4. Parking Check-In

The check-in workflow was designed as follows:

1. Receive the vehicle plate and vehicle type.
2. Validate the input.
3. Check whether the vehicle already has an active parking session.
4. Find a suitable available parking spot.
5. Create a parking ticket.
6. Mark the selected spot as occupied.
7. Return the parking ticket information to the frontend.

Vehicle type is used to support different spot categories such as standard, compact, and EV.

---

## 5. Parking Check-Out

The check-out workflow:

1. Find the active ticket using the vehicle plate.
2. Calculate the parking duration.
3. Determine the applicable parking rate.
4. Calculate the parking fee.
5. Store the checkout time and fee.
6. Mark the parking spot as available.
7. Return the completed ticket information.

This keeps ticket and parking spot state synchronized.

---

## 6. Parking Availability

The system provides availability information for the garage.

The availability logic tracks:

* Total spots
* Occupied spots
* Available spots
* EV spots
* Available EV spots

Spot filtering allows the frontend to display available or occupied spots based on the selected criteria.

---

# Assessment-Specific Implementation

## 7. T4 – Rate Card Import

### Requirement

The system should import a messy rate card and correctly store cleaned parking rates according to spot type.

### Approach

The implementation accepts rate information containing:

* Spot type
* First-hour rate
* Additional-hour rate
* Daily cap
* Original source text

The imported values are cleaned and converted into the appropriate numeric values before being stored.

### Verified Result

The rate-card test successfully created three rate records:

* Compact
* Standard
* EV

The values were persisted correctly and could be retrieved afterward.

Example cleaned rates:

| Spot Type | First Hour | Additional Hour | Daily Cap |
| --------- | ---------: | --------------: | --------: |
| Compact   |        ₹40 |             ₹20 |      ₹200 |
| Standard  |        ₹50 |             ₹30 |      ₹300 |
| EV        |        ₹60 |             ₹35 |      ₹350 |

---

## 8. T2 – Automated 24-Hour Closure and Billing

### Requirement

A nightly clock job should automatically close and bill any parking session that has been parked for more than 24 hours.

### Approach

The `/clock` endpoint was implemented as the automation trigger.

The process is:

1. Determine the clock time.
2. Calculate the 24-hour cutoff.
3. Find active sessions older than the cutoff.
4. Calculate the parking fee using the applicable rate.
5. Set the checkout time.
6. Store the calculated fee.
7. Release the parking spot.
8. Return a summary of closed sessions.

### Verified Result

A test ticket older than 24 hours was processed successfully.

The clock response showed:

* The session was automatically closed.
* A checkout time was generated.
* A parking fee was calculated.
* The parking spot was released.

The test returned:

`closed_count: 1`

and a calculated fee of:

`₹200`

This verified the automated closure and billing workflow.

---

## 9. T6 – Parking Session Transfer

### Requirement

An open parking session should be transferable to a different vehicle plate for a valet hand-off.

The parking spot and original entry time must remain unchanged.

### Approach

The transfer operation:

1. Finds the active parking session using the old plate.
2. Validates that the session is still open.
3. Changes the vehicle plate to the new plate.
4. Preserves the existing parking spot.
5. Preserves the original check-in time.
6. Keeps the session active.

### Verified Result

A test session was transferred from:

`TESTOLD111`

to:

`TESTNEW222`

The response confirmed:

* New plate preserved: `TESTNEW222`
* Original check-in time preserved.
* Original parking spot preserved.
* Session remained active.

Therefore, the valet hand-off workflow was verified.

---

# 10. Search, Sorting and Pagination

The ticket listing functionality supports:

* Searching by vehicle plate.
* Pagination.
* Sorting.
* Sort direction.

Search was tested using the `RJ14` query and returned matching parking records.

The ticket listing was also tested with sorting and pagination parameters.

---

# 11. EV Parking Support

EV parking was treated as a separate spot type.

The availability endpoint was tested for EV spots.

The test confirmed that EV availability information is returned separately, including:

* Total EV spots
* Occupied EV spots
* Available EV spots

---

# 12. Frontend Reasoning

The frontend was connected to the backend APIs through JavaScript.

The dashboard provides controls for:

* Registration
* Login
* Logout
* Vehicle check-in
* Vehicle check-out
* Ticket search
* Spot filtering
* Availability filtering
* Ticket sorting
* Parking statistics

The goal was to keep the interface simple so that the main parking workflows can be tested directly from the browser.

---

# 13. Testing Strategy

Testing was performed at multiple levels.

### Health Test

The health endpoint returned:

```text
status: ok
```

### Functional Tests

The following workflows were tested:

* Registration
* Login
* Check-in
* Check-out
* Availability
* Spot listing
* Ticket search
* Ticket sorting
* Rate-card import
* Automated 24-hour closure
* Parking session transfer
* EV availability

### Code Validation

Python syntax was checked successfully.

The application was also run through the Flask development environment and the web interface was verified in the GitHub Codespace.

---

# 14. Error Handling Considerations

The API validates important inputs and returns appropriate error responses for invalid operations.

Examples include:

* Missing required fields.
* Invalid login credentials.
* Vehicle already parked.
* Vehicle not found during checkout.
* No suitable parking spot available.
* Invalid parking session transfer.
* Invalid rate information.

The frontend displays returned messages so that the user can understand the result of an operation.

---

# 15. Repository Hygiene

The project uses `.gitignore` to prevent unnecessary or sensitive local files from being committed.

The following are excluded:

* `.venv/`
* `__pycache__/`
* `*.db`
* `cookies.txt`

Backup files such as `app.py.backup` were also kept outside the committed project files.

---

# 16. Final Implementation Status

The major required parking workflows were implemented and tested.

### Completed

* User authentication
* Parking check-in
* Parking check-out
* Parking availability
* EV availability
* Ticket search
* Ticket sorting and pagination
* T4 rate-card import
* T2 automated 24-hour closure and billing
* T6 parking session transfer
* Web dashboard
* API health check
* Repository documentation
* GitHub commit and push

The final implementation was tested in the GitHub Codespace and the working project was pushed to the `main` branch.

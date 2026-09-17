// ============================================================
// SPOTSYNC FRONTEND JAVASCRIPT
// ============================================================

const API = "";

// ============================================================
// MODALS
// ============================================================

function openLoginModal() {
    const modal = new bootstrap.Modal(
        document.getElementById("loginModal")
    );
    modal.show();
}

function openRegisterModal() {
    const modal = new bootstrap.Modal(
        document.getElementById("registerModal")
    );
    modal.show();
}

// ============================================================
// MESSAGE HELPER
// ============================================================

function showMessage(elementId, message, type = "info") {
    const element = document.getElementById(elementId);

    if (!element) return;

    element.innerHTML = `
        <div class="alert alert-${type}" role="alert">
            ${message}
        </div>
    `;
}

// ============================================================
// REGISTER
// ============================================================

document.getElementById("registerForm").addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        const name = document.getElementById("registerName").value.trim();
        const email = document.getElementById("registerEmail").value.trim();
        const password = document.getElementById("registerPassword").value;

        try {

            const response = await fetch(
                `${API}/api/register`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        name: name,
                        email: email,
                        password: password
                    })
                }
            );

            const data = await response.json();

            if (!response.ok) {
                showMessage(
                    "registerMessage",
                    data.error || "Registration failed.",
                    "danger"
                );
                return;
            }

            showMessage(
                "registerMessage",
                "Registration successful! You can now login.",
                "success"
            );

            document.getElementById("registerForm").reset();

        } catch (error) {

            showMessage(
                "registerMessage",
                "Could not connect to the server.",
                "danger"
            );
        }
    }
);

// ============================================================
// LOGIN
// ============================================================

document.getElementById("loginForm").addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        const email = document.getElementById("loginEmail").value.trim();
        const password = document.getElementById("loginPassword").value;

        try {

            const response = await fetch(
                `${API}/api/login`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    credentials: "same-origin",
                    body: JSON.stringify({
                        email: email,
                        password: password
                    })
                }
            );

            const data = await response.json();

            if (!response.ok) {
                showMessage(
                    "loginMessage",
                    data.error || "Login failed.",
                    "danger"
                );
                return;
            }

            showMessage(
                "loginMessage",
                "Login successful!",
                "success"
            );

            document.getElementById("loginForm").reset();

            setTimeout(() => {

                const modalElement =
                    document.getElementById("loginModal");

                const modal =
                    bootstrap.Modal.getInstance(modalElement);

                if (modal) {
                    modal.hide();
                }

                loadDashboard();

            }, 700);

        } catch (error) {

            showMessage(
                "loginMessage",
                "Could not connect to the server.",
                "danger"
            );
        }
    }
);

// ============================================================
// LOGOUT
// ============================================================

async function logout() {

    try {

        const response = await fetch(
            `${API}/api/logout`,
            {
                method: "POST",
                credentials: "same-origin"
            }
        );

        const data = await response.json();

        if (response.ok) {

            alert(data.message || "Logout successful.");

            location.reload();

        } else {

            alert(data.error || "Logout failed.");

        }

    } catch (error) {

        alert("Could not connect to the server.");

    }
}

// ============================================================
// CHECK-IN
// ============================================================

document.getElementById("checkInForm").addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        const plate =
            document.getElementById("checkInPlate")
            .value
            .trim()
            .toUpperCase();

        const vehicleType =
            document.getElementById("vehicleType")
            .value;

        if (!plate) {

            showMessage(
                "checkInMessage",
                "Please enter a license plate.",
                "danger"
            );

            return;
        }

        if (!vehicleType) {

            showMessage(
                "checkInMessage",
                "Please select a vehicle type.",
                "danger"
            );

            return;
        }

        try {

            const response = await fetch(
                `${API}/api/check-in`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        plate: plate,
                        vehicle_type: vehicleType,
                        garage_id: 1
                    })
                }
            );

            const data = await response.json();

            if (!response.ok) {

                showMessage(
                    "checkInMessage",
                    data.error || "Check-in failed.",
                    "danger"
                );

                return;
            }

            const ticket = data.ticket;

            showMessage(
                "checkInMessage",
                `
                <strong>Vehicle checked in successfully!</strong><br>
                Plate: ${ticket.plate}<br>
                Spot: ${ticket.spot_number}<br>
                Level: ${ticket.level}<br>
                Vehicle Type: ${ticket.vehicle_type.toUpperCase()}
                `,
                "success"
            );

            document.getElementById("checkInForm").reset();

            loadDashboard();
            loadTickets(1);

        } catch (error) {

            showMessage(
                "checkInMessage",
                "Could not connect to the server.",
                "danger"
            );

        }
    }
);

// ============================================================
// CHECK-OUT
// ============================================================

document.getElementById("checkOutForm").addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        const plate =
            document.getElementById("checkOutPlate")
            .value
            .trim()
            .toUpperCase();

        if (!plate) {

            showMessage(
                "checkOutMessage",
                "Please enter a license plate.",
                "danger"
            );

            return;
        }

        try {

            const response = await fetch(
                `${API}/api/check-out`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        plate: plate
                    })
                }
            );

            const data = await response.json();

            if (!response.ok) {

                showMessage(
                    "checkOutMessage",
                    data.error || "Check-out failed.",
                    "danger"
                );

                return;
            }

            showMessage(
                "checkOutMessage",
                `
                <strong>Vehicle checked out successfully!</strong><br>
                Plate: ${data.plate}<br>
                Duration: ${data.duration_hours} hour(s)<br>
                Fee: ₹${data.fee.toFixed(2)}<br>
                Spot: ${data.spot_number}
                `,
                "success"
            );

            document.getElementById("checkOutForm").reset();

            loadDashboard();
            loadTickets(1);

        } catch (error) {

            showMessage(
                "checkOutMessage",
                "Could not connect to the server.",
                "danger"
            );

        }
    }
);

// ============================================================
// EV AVAILABILITY
// ============================================================

async function loadEVAvailability() {

    try {

        const response = await fetch(
            `${API}/api/availability`
        );

        const data = await response.json();

        document.getElementById("evAvailable").textContent =
            data.available;

        document.getElementById("evMessage").textContent =
            data.message;

    } catch (error) {

        document.getElementById("evAvailable").textContent = "-";

        document.getElementById("evMessage").textContent =
            "Unable to load EV availability.";

    }
}

// ============================================================
// DASHBOARD
// ============================================================

async function loadDashboard() {

    try {

        const response = await fetch(
            `${API}/api/spots`
        );

        const data = await response.json();

        if (!response.ok) return;

        const spots = data.spots || [];

        const total = spots.length;

        const occupied =
            spots.filter(
                spot => spot.occupied === true
            ).length;

        const available = total - occupied;

        document.getElementById("totalSpots").textContent =
            total;

        document.getElementById("occupiedSpots").textContent =
            occupied;

        document.getElementById("availableSpots").textContent =
            available;

        loadEVAvailability();

        loadTickets(1);

    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

    }
}

// ============================================================
// LOAD SPOTS
// ============================================================

async function loadSpots() {

    const spotType =
        document.getElementById("spotTypeFilter").value;

    const availability =
        document.getElementById("availabilityFilter").value;

    let url =
        `${API}/api/spots?garage_id=1`;

    if (spotType) {
        url += `&spot_type=${encodeURIComponent(spotType)}`;
    }

    if (availability !== "") {
        url += `&available=${availability}`;
    }

    try {

        const response = await fetch(url);

        const data = await response.json();

        if (!response.ok) {

            showMessage(
                "spotsMessage",
                data.error || "Could not load spots.",
                "danger"
            );

            return;
        }

        const spots = data.spots || [];

        if (spots.length === 0) {

            document.getElementById("spotsContainer").innerHTML =
                `<p class="text-muted">No spots found.</p>`;

            return;
        }

        let html = `
            <table class="table table-bordered table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Level</th>
                        <th>Spot</th>
                        <th>Type</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        `;

        spots.forEach(spot => {

            html += `
                <tr>
                    <td>${spot.id}</td>
                    <td>${spot.level}</td>
                    <td>${spot.spot_number}</td>
                    <td>${spot.spot_type.toUpperCase()}</td>
                    <td>
                        ${
                            spot.available
                            ? '<span class="badge bg-success">Available</span>'
                            : '<span class="badge bg-danger">Occupied</span>'
                        }
                    </td>
                </tr>
            `;

        });

        html += `
                </tbody>
            </table>
        `;

        document.getElementById("spotsContainer").innerHTML =
            html;

        showMessage(
            "spotsMessage",
            `${spots.length} spot(s) found.`,
            "success"
        );

    } catch (error) {

        showMessage(
            "spotsMessage",
            "Could not connect to the server.",
            "danger"
        );

    }
}

// ============================================================
// SEARCH
// ============================================================

document.getElementById("searchForm").addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        const query =
            document.getElementById("searchQuery")
            .value
            .trim();

        if (!query) {

            showMessage(
                "searchMessage",
                "Please enter a plate number.",
                "danger"
            );

            return;
        }

        try {

            const response = await fetch(
                `${API}/api/tickets/search?q=${encodeURIComponent(query)}`
            );

            const data = await response.json();

            if (!response.ok) {

                showMessage(
                    "searchMessage",
                    data.error || "Search failed.",
                    "danger"
                );

                return;
            }

            if (data.count === 0) {

                showMessage(
                    "searchMessage",
                    "No parking records found.",
                    "warning"
                );

                return;
            }

            showMessage(
                "searchMessage",
                `${data.count} record(s) found.`,
                "success"
            );

            renderTickets(
                data.tickets
            );

        } catch (error) {

            showMessage(
                "searchMessage",
                "Could not connect to the server.",
                "danger"
            );

        }
    }
);

// ============================================================
// TICKETS
// ============================================================

async function loadTickets(page = 1) {

    const sortBy =
        document.getElementById("sortBy").value;

    const sortOrder =
        document.getElementById("sortOrder").value;

    const url =
        `${API}/api/tickets` +
        `?garage_id=1` +
        `&page=${page}` +
        `&per_page=5` +
        `&sort_by=${encodeURIComponent(sortBy)}` +
        `&order=${sortOrder}`;

    try {

        const response = await fetch(url);

        const data = await response.json();

        if (!response.ok) {

            console.error(data.error);

            return;
        }

        renderTickets(
            data.tickets || []
        );

        renderPagination(data);

    } catch (error) {

        console.error(
            "Ticket loading error:",
            error
        );

    }
}

// ============================================================
// RENDER TICKETS
// ============================================================

function renderTickets(tickets) {

    const tbody =
        document.getElementById("ticketsTableBody");

    if (!tickets || tickets.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td
                    colspan="8"
                    class="text-center text-muted"
                >
                    No records found.
                </td>
            </tr>
        `;

        return;
    }

    tbody.innerHTML = "";

    tickets.forEach(ticket => {

        const row =
            document.createElement("tr");

        row.innerHTML = `
            <td>${ticket.id}</td>

            <td>
                <strong>${ticket.plate}</strong>
            </td>

            <td>
                ${ticket.vehicle_type.toUpperCase()}
            </td>

            <td>
                ${ticket.spot_number || "-"}
            </td>

            <td>
                ${formatDate(ticket.check_in)}
            </td>

            <td>
                ${formatDate(ticket.check_out)}
            </td>

            <td>
                ${
                    ticket.fee !== null
                    ? "₹" + Number(ticket.fee).toFixed(2)
                    : "-"
                }
            </td>

            <td>
                ${
                    ticket.status === "parked"
                    ? '<span class="badge bg-success">Parked</span>'
                    : '<span class="badge bg-secondary">Checked Out</span>'
                }
            </td>
        `;

        tbody.appendChild(row);

    });
}

// ============================================================
// PAGINATION
// ============================================================

function renderPagination(data) {

    const pagination =
        document.getElementById("pagination");

    if (!data || data.pages <= 1) {

        pagination.innerHTML = "";

        return;
    }

    let html = `
        <div class="btn-group">
    `;

    if (data.has_previous) {

        html += `
            <button
                class="btn btn-outline-primary"
                onclick="loadTickets(${data.page - 1})"
            >
                Previous
            </button>
        `;

    }

    for (
        let page = 1;
        page <= data.pages;
        page++
    ) {

        html += `
            <button
                class="btn ${
                    page === data.page
                    ? "btn-primary"
                    : "btn-outline-primary"
                }"
                onclick="loadTickets(${page})"
            >
                ${page}
            </button>
        `;

    }

    if (data.has_next) {

        html += `
            <button
                class="btn btn-outline-primary"
                onclick="loadTickets(${data.page + 1})"
            >
                Next
            </button>
        `;

    }

    html += `</div>`;

    pagination.innerHTML = html;
}

// ============================================================
// DATE FORMAT
// ============================================================

function formatDate(dateString) {

    if (!dateString) {
        return "-";
    }

    const date =
        new Date(dateString);

    if (isNaN(date.getTime())) {
        return dateString;
    }

    return date.toLocaleString();
}

// ============================================================
// INITIAL LOAD
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        loadDashboard();

    }
);
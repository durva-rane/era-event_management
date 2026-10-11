const roleInfo = {
    client: {
        title: "Client Registration",
        subtitle: "Create your ERA account to plan and manage events.",
        business: false
    },
    organizer: {
        title: "Event Organizer Registration",
        subtitle: "Register to plan schedules, allocate resources and coordinate vendors.",
        business: true
    },
    venue_owner: {
        title: "Venue Owner Registration",
        subtitle: "Register your venue business and manage venue availability.",
        business: true
    },
    vendor: {
        title: "Vendor Registration",
        subtitle: "Register your event services, pricing and availability.",
        business: true
    },
    attendee: {
        title: "Attendee Registration",
        subtitle: "Create an account to receive invitations and manage RSVPs.",
        business: false
    },
    delivery_partner: {
        title: "Delivery Partner Registration",
        subtitle: "Register to receive and manage event delivery tasks.",
        business: true
    }
};

const form = document.getElementById("registrationForm");
const roleInput = document.getElementById("role");
const businessField = document.querySelector(".business-field");
const organizationInput = document.getElementById("organization");
const otpSection = document.getElementById("otpSection");
const successBox = document.getElementById("successBox");
const alertBox = document.getElementById("alert");

let selectedEmail = "";
let timerId = null;
let secondsLeft = 600;

function showAlert(message, type = "error") {
    alertBox.textContent = message;
    alertBox.className = `alert ${type === "error" ? "error-box" : "success-box-small"}`;
}

function clearAlert() {
    alertBox.textContent = "";
    alertBox.className = "alert hidden";
}

function clearErrors() {
    document.querySelectorAll(".error").forEach(el => el.textContent = "");
}

function setError(id, message) {
    const el = document.getElementById(id);
    if (el) el.textContent = message;
}

function selectRole(role) {
    const info = roleInfo[role] || roleInfo.client;
    roleInput.value = role;
    document.getElementById("formTitle").textContent = info.title;
    document.getElementById("formSubtitle").textContent = info.subtitle;

    businessField.classList.toggle("hidden", !info.business);
    organizationInput.required = info.business;

    // Toggle role-specific fields
    document.querySelectorAll(".organizer-field").forEach(el => el.classList.toggle("hidden", role !== "organizer"));
    document.querySelectorAll(".venue-field").forEach(el => el.classList.toggle("hidden", role !== "venue_owner"));
    document.querySelectorAll(".vendor-field").forEach(el => el.classList.toggle("hidden", role !== "vendor"));
    document.querySelectorAll(".client-field").forEach(el => el.classList.toggle("hidden", role !== "client"));
    
    // Toggle document upload for business stakeholders
    const requiresDoc = ["organizer", "venue_owner", "vendor"].includes(role);
    document.querySelectorAll(".doc-field").forEach(el => el.classList.toggle("hidden", !requiresDoc));

    document.querySelectorAll(".role-tab").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.role === role);
    });

    clearErrors();
    clearAlert();
}

document.querySelectorAll(".role-tab").forEach(btn => {
    btn.addEventListener("click", () => selectRole(btn.dataset.role));
});

document.querySelectorAll(".toggle-password").forEach(btn => {
    btn.addEventListener("click", () => {
        const input = document.getElementById(btn.dataset.target);
        const visible = input.type === "text";
        input.type = visible ? "password" : "text";
        btn.textContent = visible ? "Show" : "Hide";
    });
});

document.getElementById("phone").addEventListener("input", (e) => {
    e.target.value = e.target.value.replace(/\D/g, "").slice(0, 10);
});

const password = document.getElementById("password");
password.addEventListener("input", () => {
    const value = password.value;
    const rules = {
        length: value.length >= 8,
        upper: /[A-Z]/.test(value),
        lower: /[a-z]/.test(value),
        number: /\d/.test(value),
        special: /[^A-Za-z0-9]/.test(value)
    };
    Object.entries(rules).forEach(([key, valid]) => {
        document.querySelector(`[data-rule="${key}"]`).classList.toggle("valid", valid);
    });
});

function validateForm() {
    clearErrors();
    clearAlert();

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim().toLowerCase();
    const phone = document.getElementById("phone").value.trim();
    const pass = password.value;
    const confirm = document.getElementById("confirm_password").value;
    const organization = organizationInput.value.trim();
    const terms = document.getElementById("terms").checked;

    let valid = true;
    const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
    const phoneRegex = /^[6-9]\d{9}$/;

    if (!name) { setError("nameError", "Full name is required."); valid = false; }
    if (!emailRegex.test(email)) { setError("emailError", "Enter a valid email address."); valid = false; }
    if (!phoneRegex.test(phone)) { setError("phoneError", "Enter a valid 10-digit Indian mobile number."); valid = false; }

    if (roleInfo[roleInput.value].business && !organization) {
        setError("organizationError", "Business/organization name is required.");
        valid = false;
    }

    if (pass.length < 8 || !/[A-Z]/.test(pass) || !/[a-z]/.test(pass) || !/\d/.test(pass) || !/[^A-Za-z0-9]/.test(pass)) {
        setError("passwordError", "Use 8+ characters with uppercase, lowercase, number and special character.");
        valid = false;
    }

    if (pass !== confirm) {
        setError("confirmPasswordError", "Passwords do not match.");
        valid = false;
    }

    if (!terms) {
        setError("termsError", "Please accept the terms and conditions.");
        valid = false;
    }

    return valid;
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!validateForm()) return;

    const button = document.getElementById("registerBtn");
    button.disabled = true;
    button.textContent = "Processing Registration...";

    const formData = new FormData(form);

    try {
        const response = await fetch("/api/register", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            showAlert(data.message || "Registration failed.");
            return;
        }

        form.classList.add("hidden");
        alertBox.classList.add("hidden");
        successBox.classList.remove("hidden");
        document.getElementById("successMessage").textContent = data.message;

        const nextBtn = document.getElementById("newRegistrationBtn");
        nextBtn.textContent = "Proceed to Stakeholder Login →";
        nextBtn.onclick = () => { window.location.href = "/login"; };

    } catch (error) {
        showAlert("Unable to connect to the server. Make sure the application is running.");
    } finally {
        button.disabled = false;
        button.textContent = "Complete Registration →";
    }
});


function getOtp() {
    return [...document.querySelectorAll(".otp-inputs input")]
        .map(input => input.value)
        .join("");
}

document.querySelectorAll(".otp-inputs input").forEach((input, index, all) => {
    input.addEventListener("input", () => {
        input.value = input.value.replace(/\D/g, "").slice(0, 1);
        if (input.value && index < all.length - 1) all[index + 1].focus();
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Backspace" && !input.value && index > 0) {
            all[index - 1].focus();
        }
    });
});

document.getElementById("verifyBtn").addEventListener("click", async () => {
    const otp = getOtp();
    if (!/^\d{6}$/.test(otp)) {
        showAlert("Please enter the complete 6-digit OTP.");
        return;
    }

    const button = document.getElementById("verifyBtn");
    button.disabled = true;
    button.textContent = "Verifying...";

    try {
        const response = await fetch("/api/verify-otp", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({email: selectedEmail, otp})
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            showAlert(data.message || "OTP verification failed.");
            return;
        }

        otpSection.classList.add("hidden");
        alertBox.classList.add("hidden");
        successBox.classList.remove("hidden");
        document.getElementById("successMessage").textContent = data.message + " You can now continue to the ERA login page.";

    } catch (error) {
        showAlert("Unable to connect to the server.");
    } finally {
        button.disabled = false;
        button.textContent = "Verify Email & Complete Registration";
    }
});

function startTimer() {
    clearInterval(timerId);
    secondsLeft = 600;
    const timer = document.getElementById("otpTimer");
    const resend = document.getElementById("resendBtn");
    resend.disabled = true;

    timerId = setInterval(() => {
        const mins = Math.floor(secondsLeft / 60);
        const secs = secondsLeft % 60;
        timer.textContent = `OTP expires in ${mins}:${secs.toString().padStart(2, "0")}`;

        if (secondsLeft <= 0) {
            clearInterval(timerId);
            timer.textContent = "OTP expired.";
            resend.disabled = false;
        }
        secondsLeft--;
    }, 1000);
}

document.getElementById("resendBtn").addEventListener("click", async () => {
    const button = document.getElementById("resendBtn");
    button.disabled = true;

    try {
        const response = await fetch("/api/resend-otp", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({email: selectedEmail})
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            showAlert(data.message || "Could not resend OTP.");
            button.disabled = false;
            return;
        }

        showAlert("New OTP sent successfully.", "success");
        document.querySelectorAll(".otp-inputs input").forEach(i => i.value = "");
        startTimer();

    } catch (error) {
        showAlert("Unable to connect to the server.");
        button.disabled = false;
    }
});

document.getElementById("newRegistrationBtn").addEventListener("click", () => {
    window.location.reload();
});

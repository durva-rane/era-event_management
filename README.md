# ERA Event Resource & Administration System — Stakeholder Registration

This module implements the ERA registration flow with:

- Separate navigation tabs for Client, Event Organizer, Venue Owner, Vendor, Attendee and Delivery Partner.
- Client-side and server-side validation.
- Email format validation.
- Indian mobile-number validation.
- Strong password validation.
- Password hashing with Werkzeug.
- Email OTP verification.
- 10-minute OTP expiry.
- Resend OTP.
- MySQL storage.
- Role-specific registration fields.

## 1. Prerequisites

Install:

- Python 3.10+
- MySQL 8+
- A Gmail/SMTP account for sending OTP emails.

## 2. Create the database

Open MySQL and run:

    SOURCE schema.sql;

Or copy the SQL from `schema.sql` into MySQL Workbench.

## 3. Create virtual environment

Windows:

    python -m venv venv
    venv\Scripts\activate

macOS/Linux:

    python3 -m venv venv
    source venv/bin/activate

Install packages:

    pip install -r requirements.txt

## 4. Configure environment

Copy `.env.example` to `.env`.

Fill in:

    DB_PASSWORD=your_mysql_password

For Gmail, use an App Password rather than your normal Gmail password:

    SMTP_USER=your_email@gmail.com
    SMTP_PASSWORD=your_gmail_app_password

For payment integration, local development uses the mock gateway by default. To use Razorpay test mode, configure:

    PAYMENT_GATEWAY=razorpay
    RAZORPAY_KEY_ID=rzp_test_...
    RAZORPAY_KEY_SECRET=your_test_secret

Optional finance settings are `PAYMENT_CURRENCY` (default `INR`) and `INVOICE_TAX_PERCENT` (default `0`). The app does not collect or store card details.

For an existing database created from an earlier schema, apply migrations `001_vendor_booking_workflow.sql` through `004_delivery_workflow.sql` in numeric order. A fresh database gets the current tables and columns from `schema.sql`.

## 5. Run

    python app.py

Open:

    http://127.0.0.1:5000/

## Registration flow

1. User selects a stakeholder from the left navigation.
2. User enters registration details.
3. JavaScript performs immediate validation.
4. Flask validates again on the server.
5. Server checks duplicate email and phone.
6. Password is hashed.
7. Pending registration + OTP are stored.
8. OTP is emailed.
9. User enters the six-digit OTP.
10. Server verifies OTP and expiry.
11. Verified account is moved to the `users` table.

## Attendees and notifications

Organizers manage guests at `/events/<event_id>/attendees`; CSV imports require `name,email` columns and return created, duplicate, and row-error counts. Invitations include public tokenized `/rsvp/<token>` links. Registered attendees can see matching invitations at `/my/invitations`. A background worker checks every 15 minutes for events about 24 hours away; set `ENABLE_REMINDER_SCHEDULER=false` to disable it. Set `PUBLIC_BASE_URL` to the public origin used in email links. SMTP notifications are sent asynchronously; SMS currently uses a logging stub. Signed-in users can open the bell panel to read and mark notifications.

## Delivery

Organizers can create and track deliveries from `/deliveries`; delivery partners use `/delivery/tasks` to respond and advance each task through the allowed status sequence. Admins manage partner availability and activity from Admin → Delivery Partners. Partner suggestions conservatively reserve one active delivery per partner per calendar day because delivery tasks currently have a scheduled time but no duration. Task status and delay history appears in organizer tracking and is audit logged.

## Security notes

This is a project/demo registration module. For production deployment, also add:

- HTTPS.
- CSRF protection.
- Rate limiting for registration and OTP endpoints.
- OTP attempt limits.
- Audit logging.
- Secure session management.
- Account lockout / abuse controls.
- CAPTCHA or bot protection where appropriate.
- Periodic cleanup of expired pending registrations.
- Secrets stored in environment variables or a secrets manager.
- Production WSGI server instead of Flask's development server.

The implementation follows the supplied ERA SRS requirements for HTML/CSS/JavaScript + Flask + MySQL, secure password hashing, validation, role-based registration and email/SMTP integration.

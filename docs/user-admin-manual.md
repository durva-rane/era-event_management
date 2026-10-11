# User and admin manual outline

## Client and organizer

- Sign in and use the role dashboard to review events, bookings, upcoming dates, expenses, and budget usage.
- Create/edit events and schedules; select verified venues only. Search/filter venue and vendor catalogs, compare vendors, and submit booking requests.
- Manage guest lists manually or import a CSV with `name,email` columns (optional `phone`). Share invitation links; guests can RSVP without signing in.
- Track delivery tasks, event messages, invoices, payments, and event budget. Download event briefs and invoice PDFs. Use Reports to filter and export CSV/PDF.

## Venue owner and vendor

- Complete the profile and verification submission. New venues/services remain subject to verification; only verified venues and vendors appear as bookable.
- Venue owners edit listings and review bookings. Vendors maintain services and availability, then use **View/Respond Requests** to accept or reject requests. Confirmed jobs appear in the schedule and earnings summary.
- Mark work complete to enable client/organizer reviews. Check cancellation details and payment status on booking records.

## Attendee and delivery partner

- Attendees can open a unique RSVP link without an account. Registered attendees can see invitations under **My Invitations**.
- Delivery partners review assigned jobs, accept/reject, and advance only through the allowed delivery sequence. Report delays with a short explanation.

## Administrator

- Use the admin dashboard to review platform activity, pending verification queues, venues, users, bookings, payments, delivery partners, and audit records.
- Approve or reject verification submissions and venue listings. Manage delivery partner active/availability state.
- The admin-only platform report contains aggregate platform statistics, commission earned, and activity summaries. Limit access to trusted administrators.

## Operations and recovery

- Configure SMTP, payment gateway, HTTPS/proxy, and database environment settings before production use.
- Daily backups run at 02:10 after installing the cron entry. Restore only after confirming the target database; validate the restored application before resuming traffic.

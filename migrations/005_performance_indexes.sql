-- Supporting indexes for filtered dashboards, reports and high volume lists.
ALTER TABLE events
  ADD INDEX idx_events_owner_date (owner_id, event_date),
  ADD INDEX idx_events_organizer_date (organizer_id, event_date),
  ADD INDEX idx_events_status_date (status, event_date);

ALTER TABLE venues
  ADD INDEX idx_venues_search (status, location, type, capacity, price_per_hour);

ALTER TABLE bookings
  ADD INDEX idx_bookings_event_status_date (event_id, status, booking_date),
  ADD INDEX idx_bookings_vendor_status_date (vendor_id, status, booking_date),
  ADD INDEX idx_bookings_venue_status_date (venue_id, status, booking_date);

ALTER TABLE payments
  ADD INDEX idx_payments_booking_status_kind (booking_id, status, record_type),
  ADD UNIQUE INDEX uq_payments_gateway_order (gateway_order_id);

ALTER TABLE invoices
  ADD UNIQUE INDEX uq_invoices_booking (booking_id),
  ADD INDEX idx_invoices_client (client_id, issued_at);

ALTER TABLE attendees
  ADD INDEX idx_attendees_email (email),
  ADD INDEX idx_attendees_event_checkin (event_id, checked_in_at);

ALTER TABLE delivery_tasks
  ADD INDEX idx_delivery_partner_status_time (partner_id, status, scheduled_at);

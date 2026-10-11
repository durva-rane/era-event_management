-- ==============================================================================
-- ERA: Event Resource & Administration System - Seed Data
-- ==============================================================================

USE era_db;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. SEED USERS (1 Admin + 6 Role Accounts)
-- Admin Password: Admin@123
-- User Accounts Password: User@123
INSERT INTO users (id, name, email, phone, password_hash, role, status) VALUES
(1, 'System Administrator', 'admin@era.com', '9800000000', 'scrypt:32768:8:1$p1KlVOVtgk7fGpee$470b32b0a9aee4d8e1ba310bef1fa1dc3555754d28040f265260d3add22a9b97294bc10a39f081e306335642604baf58e97ab2b02061b8b28f2a7739cffd87ea', 'admin', 'active'),
(2, 'Priya Sharma (Client)', 'client@era.com', '9811111111', 'scrypt:32768:8:1$3lqeRgEuVS3vJACg$14b3303f55676801710f8c3fe03c5578010f3d5d565a0c674e32e2d2fd10c481766533dafbfaee66a09d0e3ddddff0a2616070bddb88bab822de123ea10f8385', 'client', 'active'),
(3, 'Rajesh Verma (Apex Events)', 'organizer@era.com', '9822222222', 'scrypt:32768:8:1$3lqeRgEuVS3vJACg$14b3303f55676801710f8c3fe03c5578010f3d5d565a0c674e32e2d2fd10c481766533dafbfaee66a09d0e3ddddff0a2616070bddb88bab822de123ea10f8385', 'organizer', 'active'),
(4, 'Sanjay Patel (Grand Venues)', 'venueowner@era.com', '9833333333', 'scrypt:32768:8:1$3lqeRgEuVS3vJACg$14b3303f55676801710f8c3fe03c5578010f3d5d565a0c674e32e2d2fd10c481766533dafbfaee66a09d0e3ddddff0a2616070bddb88bab822de123ea10f8385', 'venue_owner', 'active'),
(5, 'Ananya Roy (Royal Caterers)', 'vendor@era.com', '9844444444', 'scrypt:32768:8:1$3lqeRgEuVS3vJACg$14b3303f55676801710f8c3fe03c5578010f3d5d565a0c674e32e2d2fd10c481766533dafbfaee66a09d0e3ddddff0a2616070bddb88bab822de123ea10f8385', 'vendor', 'active'),
(6, 'Vikram Singh (Express Logistics)', 'delivery@era.com', '9855555555', 'scrypt:32768:8:1$3lqeRgEuVS3vJACg$14b3303f55676801710f8c3fe03c5578010f3d5d565a0c674e32e2d2fd10c481766533dafbfaee66a09d0e3ddddff0a2616070bddb88bab822de123ea10f8385', 'delivery_partner', 'active'),
(7, 'Neha Gupta (Attendee)', 'attendee@era.com', '9866666666', 'scrypt:32768:8:1$3lqeRgEuVS3vJACg$14b3303f55676801710f8c3fe03c5578010f3d5d565a0c674e32e2d2fd10c481766533dafbfaee66a09d0e3ddddff0a2616070bddb88bab822de123ea10f8385', 'attendee', 'active');

-- 2. SEED 1:1 PROFILE TABLES
INSERT INTO clients (user_id, event_requirements) VALUES
(2, 'Corporate annual conferences and luxury social galas requiring high-end AV and premium catering.');

INSERT INTO organizers (user_id, organization_name, specialization, verification_status) VALUES
(3, 'Apex Global Events LLP', 'Corporate Summits, Exhibitions & Large Conferences', 'verified');

INSERT INTO venue_owners (user_id, ownership_type, business_name, license_number, verification_status) VALUES
(4, 'corporate', 'Grand Heritage Hospitality Group', 'MUM-LIC-VN-2024-8891', 'verified');

INSERT INTO vendors (user_id, business_name, service_type, description, pricing, location, verification_status) VALUES
(5, 'Royal Feast Catering & Hospitality', 'Catering', 'Gourmet multi-cuisine live counters, buffet setups and fine-dining experiences.', 1200.00, 'Mumbai, Maharashtra', 'verified');

INSERT INTO delivery_partners (user_id, availability, status) VALUES
(6, 'available', 'active');

-- 3. SEED VERIFICATION DOCUMENTS
INSERT INTO verification_documents (id, user_id, file_path, status, reviewed_by, remarks) VALUES
(1, 3, '/uploads/docs/organizer_reg_certificate.pdf', 'approved', 1, 'Verified MCA registration and corporate GST document.'),
(2, 4, '/uploads/docs/venue_license_deed.pdf', 'approved', 1, 'Fire safety license and municipal clearance verified.'),
(3, 5, '/uploads/docs/fssai_license.pdf', 'approved', 1, 'FSSAI central food safety registration valid until 2028.');

-- 4. SEED VENUES
INSERT INTO venues (id, owner_id, name, type, location, capacity, price_per_hour, status) VALUES
(1, 4, 'Grand Crystal Ballroom', 'Ballroom', 'Bandra Kurla Complex, Mumbai', 500, 15000.00, 'verified'),
(2, 4, 'Skyline Horizon Arena', 'Arena', 'Worli Sea Face, Mumbai', 2500, 45000.00, 'verified'),
(3, 4, 'Emerald Garden Pavilion', 'Pavilion', 'Juhu Beach Road, Mumbai', 250, 9500.00, 'verified');

-- 5. SEED VENDOR SERVICES
INSERT INTO vendor_services (id, vendor_id, name, price, description) VALUES
(1, 5, 'Executive Corporate Buffet (Per Plate)', 1250.00, 'Comprehensive lunch/dinner with salad bar, 3 mains, live pasta counter, and dessert spread.'),
(2, 5, 'High-Tea & Artisan Snacks Package (Per Head)', 450.00, 'Premium tea/coffee, mocktails, freshly baked petit fours and savories.'),
(3, 5, 'VIP Presidential Lounge Banquet (Per Head)', 2800.00, 'Fine dining 5-course plated dinner with dedicated sommelier service.');

-- 6. SEED VENDOR AVAILABILITY
INSERT INTO vendor_availability (id, vendor_id, date, start_time, end_time) VALUES
(1, 5, '2026-11-15', '07:00:00', '23:00:00'),
(2, 5, '2026-11-16', '07:00:00', '23:00:00'),
(3, 5, '2026-12-05', '10:00:00', '23:30:00');

-- 7. SEED EVENTS
INSERT INTO events (id, owner_id, organizer_id, venue_id, name, category, description, event_date, start_time, end_time, expected_attendees, status, live_status) VALUES
(1, 2, 3, 1, 'Global Tech & AI Summit 2026', 'Corporate', 'Annual high-technology keynote, technical panels, and AI startup showcase.', '2026-11-15', '09:00:00', '18:00:00', 450, 'confirmed', 'upcoming'),
(2, 2, 3, 3, 'Royal Wedding Gala & Sangeet', 'Wedding', 'Exclusive luxury celebration with bespoke decor and multi-cuisine hospitality.', '2026-12-05', '17:00:00', '23:30:00', 220, 'planned', 'upcoming');

-- 8. SEED SCHEDULE ITEMS
INSERT INTO event_schedule_items (id, event_id, title, start_time, end_time) VALUES
(1, 1, 'Delegate Check-in & Breakfast Networking', '09:00:00', '10:00:00'),
(2, 1, 'Keynote Address: Autonomous Systems & Generative AI', '10:00:00', '11:30:00'),
(3, 1, 'Executive Networking Lunch (Catering Area)', '13:00:00', '14:30:00'),
(4, 1, 'Panel: Security in Cloud & Enterprise Applications', '14:30:00', '16:00:00'),
(5, 1, 'Closing Remarks & Awards Ceremony', '17:00:00', '18:00:00');

-- 9. SEED BOOKINGS
INSERT INTO bookings (id, event_id, booking_type, venue_id, vendor_id, service_id, booking_date, start_time, end_time, amount, status, payment_status, commission_amount) VALUES
(1, 1, 'venue', 1, NULL, NULL, '2026-11-15', '09:00:00', '18:00:00', 135000.00, 'confirmed', 'paid', 6750.00),
(2, 1, 'vendor', NULL, 5, 1, '2026-11-15', '12:30:00', '15:30:00', 562500.00, 'confirmed', 'partially_paid', 28125.00),
(3, 2, 'venue', 3, NULL, NULL, '2026-12-05', '17:00:00', '23:30:00', 61750.00, 'requested', 'payment_pending', 3087.50);

-- 10. SEED BUDGETS & BUDGET ITEMS
INSERT INTO budgets (id, event_id, total_amount) VALUES
(1, 1, 1500000.00),
(2, 2, 2500000.00);

INSERT INTO budget_items (id, budget_id, category, allocated_amount, spent_amount) VALUES
(1, 1, 'Venue Rental', 200000.00, 135000.00),
(2, 1, 'Catering & Beverages', 650000.00, 562500.00),
(3, 1, 'Audio/Visual & Stage Production', 350000.00, 280000.00),
(4, 1, 'Marketing & Delegate Kits', 200000.00, 120000.00),
(5, 1, 'Contingency & Logistics', 100000.00, 45000.00);

-- 11. SEED PAYMENTS & INVOICES
INSERT INTO payments (id, booking_id, amount, method, status, transaction_id, paid_at) VALUES
(1, 1, 135000.00, 'net_banking', 'success', 'TXN-ERA-20261115-001', CURRENT_TIMESTAMP),
(2, 2, 300000.00, 'upi', 'success', 'TXN-ERA-20261115-002', CURRENT_TIMESTAMP);

INSERT INTO invoices (id, booking_id, invoice_no, tax, total, issued_at) VALUES
(1, 1, 'INV-ERA-2026-0001', 24300.00, 159300.00, CURRENT_TIMESTAMP),
(2, 2, 'INV-ERA-2026-0002', 101250.00, 663750.00, CURRENT_TIMESTAMP);

-- 12. SEED ATTENDEES
INSERT INTO attendees (id, event_id, name, email, phone, invitation_status, rsvp_status, checked_in_at, checked_out_at) VALUES
(1, 1, 'Neha Gupta', 'attendee@era.com', '9866666666', 'registered', 'accepted', NULL, NULL),
(2, 1, 'Rohan Mehta', 'rohan.mehta@example.com', '9877777777', 'registered', 'accepted', NULL, NULL),
(3, 1, 'Tanvi Kulkarni', 'tanvi.k@example.com', '9888888888', 'invited', 'pending', NULL, NULL),
(4, 2, 'Aarav Singhania', 'aarav.s@example.com', '9899999999', 'registered', 'accepted', NULL, NULL);

-- 13. SEED DELIVERY TASKS
INSERT INTO delivery_tasks (id, event_id, partner_id, pickup, destination, scheduled_at, item_description, quantity, instructions, status) VALUES
(1, 1, 6, 'Apex Logistics Hub, Goregaon', 'Grand Crystal Ballroom, BKC', '2026-11-15 06:30:00', 'Stage LED Panels & 4K Truss Rigging Gear', 12, 'Handle with care; deliver directly to backstage loading bay dock 2.', 'accepted'),
(2, 1, 6, 'Royal Feast Central Kitchen, Andheri', 'Grand Crystal Ballroom, BKC', '2026-11-15 11:30:00', 'Insulated Chafing Dishes, Cutlery & Buffet Glassware', 45, 'Temperature-sensitive containers; hand over to Chef Deepak.', 'assigned');

-- 14. SEED REVIEWS
INSERT INTO reviews (id, booking_id, reviewer_id, vendor_id, rating, comment) VALUES
(1, 1, 2, 4, 5, 'Superb hospitality, state-of-the-art acoustic setup, and seamless coordination by the venue staff.');

-- 15. SEED CHAT MESSAGES
INSERT INTO chat_messages (id, event_id, sender_id, receiver_id, message, sent_at) VALUES
(1, 1, 2, 3, 'Hi Rajesh, please confirm if the keynote speaker presentation deck has been tested on the main LED screen.', CURRENT_TIMESTAMP),
(2, 1, 3, 2, 'Hello Priya! Yes, AV testing concluded today morning with zero latency. Everything is set.', CURRENT_TIMESTAMP);

-- 16. SEED NOTIFICATIONS
INSERT INTO notifications (id, user_id, message, status) VALUES
(1, 2, 'Your venue booking for Grand Crystal Ballroom has been confirmed.', 'unread'),
(2, 3, 'A new delivery task has been scheduled for Global Tech & AI Summit 2026.', 'read'),
(3, 5, 'You received a new catering booking request for Global Tech & AI Summit 2026.', 'unread');

-- 17. SEED AUDIT LOGS
INSERT INTO audit_logs (id, user_id, action, entity, entity_id, result) VALUES
(1, 1, 'SYSTEM_INIT', 'schema', 1, 'success'),
(2, 2, 'CREATE_EVENT', 'events', 1, 'success'),
(3, 2, 'BOOK_VENUE', 'bookings', 1, 'success'),
(4, 4, 'CONFIRM_BOOKING', 'bookings', 1, 'success');

SET FOREIGN_KEY_CHECKS = 1;

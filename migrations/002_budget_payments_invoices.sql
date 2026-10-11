-- Apply once after migration 001 to an existing ERA database.
ALTER TABLE bookings
    MODIFY COLUMN payment_status ENUM('payment_pending','partially_paid','paid','refunded') NOT NULL DEFAULT 'payment_pending',
    ADD COLUMN quantity INT UNSIGNED NOT NULL DEFAULT 1 AFTER end_time,
    ADD COLUMN budget_category VARCHAR(100) NULL AFTER quantity;

ALTER TABLE budgets
    ADD COLUMN alert_80_sent BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN alert_exceeded_sent BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE budget_items
    ADD COLUMN estimated_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER allocated_amount;

ALTER TABLE payments
    MODIFY COLUMN method ENUM('upi','net_banking','card','cash','bank_transfer','razorpay','mock') NOT NULL,
    MODIFY COLUMN transaction_id VARCHAR(100) NULL,
    ADD COLUMN gateway_order_id VARCHAR(100) NULL AFTER transaction_id,
    ADD COLUMN record_type ENUM('charge','refund') NOT NULL DEFAULT 'charge' AFTER gateway_order_id,
    ADD COLUMN parent_payment_id BIGINT UNSIGNED NULL AFTER record_type,
    ADD COLUMN initiated_by BIGINT UNSIGNED NULL AFTER parent_payment_id,
    ADD COLUMN expires_at DATETIME NULL AFTER initiated_by,
    ADD CONSTRAINT fk_payments_parent FOREIGN KEY (parent_payment_id) REFERENCES payments(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_payments_initiated_by FOREIGN KEY (initiated_by) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE invoices
    ADD COLUMN event_name VARCHAR(200) NULL AFTER invoice_no,
    ADD COLUMN client_id BIGINT UNSIGNED NULL AFTER event_name,
    ADD COLUMN vendor_id BIGINT UNSIGNED NULL AFTER client_id,
    ADD COLUMN description TEXT NULL AFTER vendor_id,
    ADD COLUMN quantity INT UNSIGNED NOT NULL DEFAULT 1 AFTER description,
    ADD COLUMN amount DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER quantity,
    ADD COLUMN payment_status ENUM('payment_pending','partially_paid','paid','refunded') NOT NULL DEFAULT 'payment_pending' AFTER total;

UPDATE invoices i JOIN bookings b ON b.id=i.booking_id JOIN events e ON e.id=b.event_id
SET i.event_name=e.name,i.client_id=e.owner_id,i.vendor_id=b.vendor_id,
    i.description=COALESCE((SELECT vs.name FROM vendor_services vs WHERE vs.id=b.service_id),
                           (SELECT v.name FROM venues v WHERE v.id=b.venue_id)),
    i.quantity=b.quantity,i.amount=b.amount;

ALTER TABLE invoices
    MODIFY COLUMN event_name VARCHAR(200) NOT NULL,
    MODIFY COLUMN client_id BIGINT UNSIGNED NOT NULL,
    ADD CONSTRAINT fk_invoices_client FOREIGN KEY (client_id) REFERENCES users(id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_invoices_vendor FOREIGN KEY (vendor_id) REFERENCES users(id) ON DELETE SET NULL;

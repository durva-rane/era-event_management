-- Apply once to databases created from the original ERA schema.
-- Fresh databases receive these columns and index directly from schema.sql.
ALTER TABLE bookings
    MODIFY COLUMN status ENUM('pending', 'requested', 'confirmed', 'rejected', 'cancelled', 'completed') NOT NULL DEFAULT 'pending',
    ADD COLUMN cancelled_by BIGINT UNSIGNED NULL AFTER commission_amount,
    ADD COLUMN cancellation_reason TEXT NULL AFTER cancelled_by,
    ADD COLUMN cancelled_at DATETIME NULL AFTER cancellation_reason,
    ADD CONSTRAINT fk_bookings_cancelled_by FOREIGN KEY (cancelled_by) REFERENCES users(id) ON DELETE SET NULL,
    ADD INDEX idx_bookings_vendor_conflict (vendor_id, booking_date, start_time, end_time, status);

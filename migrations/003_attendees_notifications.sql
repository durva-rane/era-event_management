-- Apply once after migrations 001 and 002 to an existing ERA database.
ALTER TABLE attendees
    ADD COLUMN rsvp_token VARCHAR(64) NULL AFTER phone,
    ADD UNIQUE KEY uq_attendee_rsvp_token (rsvp_token);

CREATE TABLE event_reminders (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id BIGINT UNSIGNED NOT NULL,
    attendee_id BIGINT UNSIGNED NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reminder_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    CONSTRAINT fk_reminder_attendee FOREIGN KEY (attendee_id) REFERENCES attendees(id) ON DELETE CASCADE,
    UNIQUE KEY uq_event_attendee_reminder (event_id, attendee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE notifications
    ADD COLUMN event_type VARCHAR(60) NOT NULL DEFAULT 'general' AFTER message,
    ADD COLUMN link VARCHAR(500) NULL AFTER event_type;

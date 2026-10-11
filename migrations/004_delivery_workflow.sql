-- Apply once after migrations 001 through 003 to an existing ERA database.
ALTER TABLE delivery_tasks
    MODIFY COLUMN status ENUM(
        'assigned','accepted','rejected','pickup_pending','picked_up',
        'in_transit','delivered','failed','cancelled'
    ) NOT NULL DEFAULT 'assigned';

CREATE TABLE delivery_task_updates (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT UNSIGNED NOT NULL,
    update_type ENUM('assigned','status','delayed') NOT NULL,
    from_status VARCHAR(30) NULL,
    to_status VARCHAR(30) NULL,
    note TEXT NULL,
    actor_id BIGINT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_delivery_update_task FOREIGN KEY (task_id) REFERENCES delivery_tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_delivery_update_actor FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_delivery_update_timeline (task_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

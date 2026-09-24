SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS activities (
    activity_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    starts_at DATETIME(6) NOT NULL,
    ends_at DATETIME(6) NOT NULL,
    capacity INT UNSIGNED NOT NULL,
    reserved_count INT UNSIGNED NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT chk_activity_capacity CHECK (reserved_count <= capacity),
    CONSTRAINT chk_activity_time CHECK (ends_at > starts_at)
);

CREATE TABLE IF NOT EXISTS reservations (
    reservation_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    activity_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_reservations_activity FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
    CONSTRAINT uq_reservations_activity_user UNIQUE (activity_id, user_id)
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    activity_id VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    request_fingerprint CHAR(64) NOT NULL,
    http_status SMALLINT UNSIGNED NOT NULL,
    response_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (activity_id, idempotency_key),
    CONSTRAINT fk_idempotency_activity FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
);

INSERT INTO activities (activity_id, name, starts_at, ends_at, capacity)
VALUES ('activity-001', '云平台实践资源预约', '2025-01-01 00:00:00.000000', '2099-01-01 00:00:00.000000', 2)
ON DUPLICATE KEY UPDATE activity_id = activity_id;

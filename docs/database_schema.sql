CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS stations (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(12) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    state VARCHAR(80),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trains (
    id BIGSERIAL PRIMARY KEY,
    number VARCHAR(12) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    origin_station_code VARCHAR(12) NOT NULL,
    destination_station_code VARCHAR(12) NOT NULL,
    service_days JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS route_segments (
    id BIGSERIAL PRIMARY KEY,
    train_id BIGINT NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    station_id BIGINT NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    distance_km INTEGER NOT NULL,
    arrival_time VARCHAR(8),
    departure_time VARCHAR(8),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_route_segments_train_sequence UNIQUE (train_id, sequence),
    CONSTRAINT uq_route_segments_train_station UNIQUE (train_id, station_id)
);

CREATE INDEX IF NOT EXISTS ix_route_segments_train_id ON route_segments(train_id);
CREATE INDEX IF NOT EXISTS ix_route_segments_station_id ON route_segments(station_id);

CREATE TABLE IF NOT EXISTS availabilities (
    id BIGSERIAL PRIMARY KEY,
    train_id BIGINT NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    source_station_id BIGINT NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    destination_station_id BIGINT NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    travel_date DATE NOT NULL,
    travel_class VARCHAR(12) NOT NULL,
    status VARCHAR(32) NOT NULL,
    available_count INTEGER,
    rac_count INTEGER,
    waitlist_count INTEGER,
    provider VARCHAR(40) NOT NULL DEFAULT 'mock',
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_availability_lookup UNIQUE (
        train_id,
        source_station_id,
        destination_station_id,
        travel_date,
        travel_class
    )
);

CREATE INDEX IF NOT EXISTS ix_availabilities_travel_date ON availabilities(travel_date);
CREATE INDEX IF NOT EXISTS ix_availabilities_train_id ON availabilities(train_id);

CREATE TABLE IF NOT EXISTS availability_snapshots (
    id BIGSERIAL PRIMARY KEY,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    train_number VARCHAR(12) NOT NULL,
    source_station_code VARCHAR(12) NOT NULL,
    destination_station_code VARCHAR(12) NOT NULL,
    travel_date DATE NOT NULL,
    travel_class VARCHAR(12) NOT NULL,
    status VARCHAR(32) NOT NULL,
    available_count INTEGER,
    rac_count INTEGER,
    waitlist_count INTEGER,
    provider VARCHAR(40) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_availability_snapshots_observed_at
    ON availability_snapshots(observed_at);
CREATE INDEX IF NOT EXISTS ix_availability_snapshots_lookup
    ON availability_snapshots(
        train_number,
        source_station_code,
        destination_station_code,
        travel_date,
        travel_class,
        observed_at DESC
    );

CREATE TABLE IF NOT EXISTS user_monitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(80),
    train_number VARCHAR(12),
    source_station_code VARCHAR(12) NOT NULL,
    destination_station_code VARCHAR(12) NOT NULL,
    travel_date DATE NOT NULL,
    travel_class VARCHAR(12) NOT NULL,
    threshold_status VARCHAR(32) NOT NULL DEFAULT 'RAC',
    notification_target VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_checked_at TIMESTAMPTZ,
    last_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_user_monitors_user_id ON user_monitors(user_id);
CREATE INDEX IF NOT EXISTS ix_user_monitors_train_number ON user_monitors(train_number);
CREATE INDEX IF NOT EXISTS ix_user_monitors_travel_date ON user_monitors(travel_date);

CREATE TABLE IF NOT EXISTS recommendations (
    id BIGSERIAL PRIMARY KEY,
    monitor_id UUID REFERENCES user_monitors(id) ON DELETE SET NULL,
    train_number VARCHAR(12) NOT NULL,
    source_station_code VARCHAR(12) NOT NULL,
    destination_station_code VARCHAR(12) NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    explanation VARCHAR(1000) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_recommendations_monitor_id ON recommendations(monitor_id);
CREATE INDEX IF NOT EXISTS ix_recommendations_train_number ON recommendations(train_number);

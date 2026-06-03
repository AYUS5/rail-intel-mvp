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


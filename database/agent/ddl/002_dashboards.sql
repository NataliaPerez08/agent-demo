BEGIN;

CREATE TABLE IF NOT EXISTS dashboards (
    id BIGSERIAL PRIMARY KEY,

    name VARCHAR(200) NOT NULL,
    description TEXT,

    user_id VARCHAR(100) NOT NULL DEFAULT 'anon',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dashboards_user
    ON dashboards(user_id);

CREATE TABLE IF NOT EXISTS dashboard_widgets (
    id BIGSERIAL PRIMARY KEY,

    dashboard_id BIGINT NOT NULL
        REFERENCES dashboards(id)
        ON DELETE CASCADE,

    title VARCHAR(200) NOT NULL,
    question TEXT NOT NULL,

    chart_type VARCHAR(50),
    chart_config JSONB,

    position INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_widgets_dashboard
    ON dashboard_widgets(dashboard_id);

CREATE INDEX IF NOT EXISTS idx_widgets_position
    ON dashboard_widgets(dashboard_id, position);

COMMIT;
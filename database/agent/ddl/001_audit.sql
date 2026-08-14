BEGIN;

CREATE TABLE IF NOT EXISTS analytics_query_log (
    id BIGSERIAL PRIMARY KEY,

    request_id VARCHAR(100),

    user_id VARCHAR(100) NOT NULL,
    thread_id VARCHAR(100) NOT NULL,

    question TEXT NOT NULL,
    generated_sql TEXT,

    successful BOOLEAN NOT NULL DEFAULT FALSE,
    error TEXT,

    execution_ms INTEGER NOT NULL DEFAULT 0,
    row_count INTEGER NOT NULL DEFAULT 0,

    model VARCHAR(100),
    retry_count INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_created
    ON analytics_query_log(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_log_thread
    ON analytics_query_log(thread_id);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at
    ON analytics_query_log(created_at);

CREATE INDEX IF NOT EXISTS idx_audit_log_request_id
    ON analytics_query_log(request_id);

COMMIT;
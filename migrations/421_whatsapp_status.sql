-- PostgreSQL. Also applied idempotently by nowup_whatsapp_status421.initialize
-- through the project's SQLite/PostgreSQL adapter during init_db/startup.
CREATE TABLE IF NOT EXISTS whatsapp_status_settings421 (
    professional_id BIGINT PRIMARY KEY REFERENCES professionals(id) ON DELETE CASCADE,
    enabled BIGINT NOT NULL DEFAULT 1,
    templates_json TEXT NOT NULL DEFAULT '{}'
);
-- No orders or queue statuses are changed by this migration.

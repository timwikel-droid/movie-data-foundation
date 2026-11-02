-- Template: least-privilege roles if MoodBox runs PostgreSQL (SQLite has no role system).
-- Adjust names/schemas to MoodBox's environment and have the senior technical advisor review before use.
CREATE ROLE app_writer    NOLOGIN;  -- product backend: inserts events, no bulk reads
CREATE ROLE pipeline_rw   NOLOGIN;  -- scheduled ETL / quality checks
CREATE ROLE analyst_ro    NOLOGIN;  -- analysts: consent-filtered views only
CREATE ROLE privacy_admin NOLOGIN;  -- runs deletion/retention jobs; access logged and reviewed

GRANT INSERT ON sessions, mood_checkins, recommendations, ratings TO app_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pipeline_rw;
GRANT SELECT ON v_checkin_facts, v_rec_facts, v_rating_facts TO analyst_ro;
REVOKE ALL ON users FROM analyst_ro;            -- email_hash is never exposed to analysts
GRANT SELECT, DELETE ON ALL TABLES IN SCHEMA public TO privacy_admin;
GRANT INSERT ON deletion_log TO privacy_admin;

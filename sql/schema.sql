-- MoodBox data foundation: clean, constrained schema (SQLite dialect; portable to PostgreSQL with minor changes).
-- Raw data lands in stg_* tables (no constraints). Only rows that pass the quality checks reach these tables.
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_rating_facts;
DROP VIEW  IF EXISTS v_rec_facts;
DROP VIEW  IF EXISTS v_checkin_facts;
DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS recommendations;
DROP TABLE IF EXISTS mood_checkins;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS movies;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id           TEXT PRIMARY KEY,
    email_hash        TEXT NOT NULL UNIQUE,            -- salted SHA-256; the only identifier kept
    age_band          TEXT NOT NULL CHECK (age_band IN ('18-24','25-34','35-44','45-54','55+')),
    region            TEXT NOT NULL CHECK (region IN ('NL','Other Canada','International')),
    created_at        TEXT NOT NULL,
    consent_analytics INTEGER NOT NULL CHECK (consent_analytics IN (0,1)),
    consent_at        TEXT
);

CREATE TABLE movies (
    movie_id     TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    genre        TEXT NOT NULL CHECK (genre IN
                 ('comedy','drama','thriller','romance','action','documentary','animation','horror','sci-fi')),
    release_year INTEGER CHECK (release_year BETWEEN 1900 AND 2030),
    runtime_min  INTEGER CHECK (runtime_min > 0)
);

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    started_at TEXT NOT NULL,
    device     TEXT CHECK (device IN ('mobile','desktop','tablet'))
);

CREATE TABLE mood_checkins (
    checkin_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    mood       TEXT NOT NULL CHECK (mood IN
               ('happy','sad','stressed','relaxed','excited','bored','nostalgic','anxious')),
    intensity  INTEGER NOT NULL CHECK (intensity BETWEEN 1 AND 5),
    created_at TEXT NOT NULL
);

CREATE TABLE recommendations (
    rec_id     TEXT PRIMARY KEY,
    checkin_id TEXT NOT NULL REFERENCES mood_checkins(checkin_id) ON DELETE CASCADE,
    movie_id   TEXT NOT NULL REFERENCES movies(movie_id),
    rank       INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 10),
    shown_at   TEXT NOT NULL
);

CREATE TABLE ratings (
    rating_id TEXT PRIMARY KEY,
    rec_id    TEXT NOT NULL UNIQUE REFERENCES recommendations(rec_id) ON DELETE CASCADE,
    user_id   TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    rating    INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    rated_at  TEXT NOT NULL
);

CREATE INDEX idx_sessions_user  ON sessions(user_id);
CREATE INDEX idx_checkins_sess  ON mood_checkins(session_id);
CREATE INDEX idx_checkins_user  ON mood_checkins(user_id);
CREATE INDEX idx_recs_checkin   ON recommendations(checkin_id);
CREATE INDEX idx_ratings_user   ON ratings(user_id);

-- Audit tables (kept across rebuilds)
CREATE TABLE IF NOT EXISTS quality_issues (
    run_at       TEXT NOT NULL,
    check_id     TEXT NOT NULL,
    table_name   TEXT NOT NULL,
    severity     TEXT NOT NULL,
    description  TEXT NOT NULL,
    rows_flagged INTEGER NOT NULL,
    rows_total   INTEGER NOT NULL
);

-- Holds NO personal data: only a one-way hash of the user id, so a restored backup can be re-purged.
CREATE TABLE IF NOT EXISTS deletion_log (
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_hash    TEXT,
    action       TEXT NOT NULL,
    rows_deleted TEXT NOT NULL,
    processed_at TEXT NOT NULL
);

-- Analyst-facing views: consent-filtered, no email_hash, no user_id.
CREATE VIEW v_checkin_facts AS
SELECT c.checkin_id, c.mood, c.intensity, u.age_band, u.region, c.created_at
FROM mood_checkins c JOIN users u ON u.user_id = c.user_id
WHERE u.consent_analytics = 1;

CREATE VIEW v_rec_facts AS
SELECT rec.rec_id, c.mood, c.intensity, m.genre, rec.rank, r.rating, u.age_band, u.region, rec.shown_at
FROM recommendations rec
JOIN mood_checkins c ON c.checkin_id = rec.checkin_id
JOIN movies m        ON m.movie_id   = rec.movie_id
JOIN users u         ON u.user_id    = c.user_id
LEFT JOIN ratings r  ON r.rec_id     = rec.rec_id
WHERE u.consent_analytics = 1;

CREATE VIEW v_rating_facts AS
SELECT * FROM v_rec_facts WHERE rating IS NOT NULL;

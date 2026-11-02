"""Load raw CSVs into staging tables and run SQL data-quality checks against them.

Each check is a query returning one row per offending record. Severity:
  error  - record is rejected from the clean tables
  policy - record is kept but excluded from analytics (consent)
  info   - funnel/tracking signal worth monitoring, not rejected
"""
from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd

TABLES = ["users", "movies", "sessions", "mood_checkins", "recommendations", "ratings"]
_USERS = "(SELECT user_id, MIN(created_at) AS created_at, MIN(consent_analytics) AS consent_analytics FROM stg_users GROUP BY user_id)"
_MOODS = "('happy','sad','stressed','relaxed','excited','bored','nostalgic','anxious')"

# (check_id, table, severity, description, offending-rows query)
CHECKS = [
    ("DUP_USER_ID", "users", "error", "Duplicate user_id rows",
     "SELECT user_id FROM stg_users WHERE rowid NOT IN (SELECT MIN(rowid) FROM stg_users GROUP BY user_id)"),
    ("DUP_EMAIL_HASH", "users", "error", "Different user_ids sharing one email_hash (double sign-up)",
     "SELECT a.user_id FROM stg_users a JOIN stg_users b ON a.email_hash=b.email_hash AND a.user_id<b.user_id"),
    ("DUP_SESSION_ID", "sessions", "error", "Duplicate session_id rows (double-fired tracking event)",
     "SELECT session_id FROM stg_sessions WHERE rowid NOT IN (SELECT MIN(rowid) FROM stg_sessions GROUP BY session_id)"),
    ("ORPHAN_SESSION_USER", "sessions", "error", "Session references a user that does not exist",
     "SELECT session_id FROM stg_sessions WHERE user_id NOT IN (SELECT user_id FROM stg_users)"),
    ("SESSION_BEFORE_SIGNUP", "sessions", "error", "Session starts before the user's sign-up time (clock/tracking error)",
     f"SELECT s.session_id FROM stg_sessions s JOIN {_USERS} u ON u.user_id=s.user_id WHERE s.started_at < u.created_at"),
    ("ORPHAN_CHECKIN_SESSION", "mood_checkins", "error", "Mood check-in references a missing session",
     "SELECT checkin_id FROM stg_mood_checkins WHERE session_id NOT IN (SELECT session_id FROM stg_sessions)"),
    ("MISSING_MOOD", "mood_checkins", "error", "Mood is missing or not in the allowed list",
     f"SELECT checkin_id FROM stg_mood_checkins WHERE mood IS NULL OR mood NOT IN {_MOODS}"),
    ("INTENSITY_RANGE", "mood_checkins", "error", "Intensity missing or outside 1-5",
     "SELECT checkin_id FROM stg_mood_checkins WHERE intensity IS NULL OR intensity NOT BETWEEN 1 AND 5"),
    ("ORPHAN_REC_CHECKIN", "recommendations", "error", "Recommendation references a missing check-in",
     "SELECT rec_id FROM stg_recommendations WHERE checkin_id NOT IN (SELECT checkin_id FROM stg_mood_checkins)"),
    ("ORPHAN_RATING_REC", "ratings", "error", "Rating references a recommendation that was never logged (tracking gap)",
     "SELECT rating_id FROM stg_ratings WHERE rec_id NOT IN (SELECT rec_id FROM stg_recommendations)"),
    ("RATING_RANGE", "ratings", "error", "Rating missing or outside 1-5",
     "SELECT rating_id FROM stg_ratings WHERE rating IS NULL OR rating NOT BETWEEN 1 AND 5"),
    ("RATING_BEFORE_SHOWN", "ratings", "error", "Rating timestamped before the recommendation was shown",
     "SELECT r.rating_id FROM stg_ratings r JOIN stg_recommendations rec ON rec.rec_id=r.rec_id WHERE r.rated_at < rec.shown_at"),
    ("RATING_USER_MISMATCH", "ratings", "error", "Rating's user differs from the user who got the recommendation",
     "SELECT r.rating_id FROM stg_ratings r JOIN stg_recommendations rec ON rec.rec_id=r.rec_id "
     "JOIN stg_mood_checkins c ON c.checkin_id=rec.checkin_id WHERE c.user_id <> r.user_id"),
    ("SESSION_NO_CHECKIN", "sessions", "info", "Sessions with no mood check-in (funnel drop-off; monitor the rate)",
     "SELECT DISTINCT session_id FROM stg_sessions WHERE session_id NOT IN (SELECT session_id FROM stg_mood_checkins)"),
    ("NO_ANALYTICS_CONSENT", "sessions", "policy", "Sessions from users without analytics consent (excluded from reports)",
     f"SELECT DISTINCT s.session_id FROM stg_sessions s JOIN {_USERS} u ON u.user_id=s.user_id WHERE u.consent_analytics=0"),
]


def load_staging(conn: sqlite3.Connection, raw_dir: Path) -> dict[str, int]:
    counts = {}
    for t in TABLES:
        df = pd.read_csv(Path(raw_dir) / f"{t}.csv")
        df.to_sql(f"stg_{t}", conn, if_exists="replace", index=False)
        counts[t] = len(df)
    return counts


def run_checks(conn: sqlite3.Connection) -> pd.DataFrame:
    """Run every check, persist results to quality_issues (created by sql/schema.sql), return a DataFrame."""
    run_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    rows = []
    for cid, table, sev, desc, sql in CHECKS:
        flagged = conn.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]
        total = conn.execute(f"SELECT COUNT(*) FROM stg_{table}").fetchone()[0]
        rows.append((run_at, cid, table, sev, desc, flagged, total))
    conn.executemany("INSERT INTO quality_issues VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    df = pd.DataFrame(rows, columns=["run_at", "check_id", "table", "severity", "description", "rows_flagged", "rows_total"])
    df["pct_of_table"] = (100 * df.rows_flagged / df.rows_total).round(2)
    return df


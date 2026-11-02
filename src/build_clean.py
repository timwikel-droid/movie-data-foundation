"""Promote staging rows into the constrained schema. Rows failing a rule are dropped (and counted)."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

SCHEMA = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
_MOODS = "('happy','sad','stressed','relaxed','excited','bored','nostalgic','anxious')"
_FIRST = lambda t, k: f"{t}.rowid IN (SELECT MIN(rowid) FROM {t} GROUP BY {k})"  # keep first of each duplicate key

INSERTS = [
    ("movies", """INSERT INTO movies SELECT movie_id, title, genre, CAST(release_year AS INTEGER), CAST(runtime_min AS INTEGER)
                  FROM stg_movies"""),
    ("users", f"""INSERT INTO users SELECT user_id, email_hash, age_band, region, created_at,
                  CAST(consent_analytics AS INTEGER), consent_at FROM stg_users
                  WHERE {_FIRST('stg_users', 'user_id')}"""),
    ("sessions", f"""INSERT INTO sessions SELECT s.session_id, s.user_id, s.started_at, s.device
                  FROM stg_sessions s JOIN users u ON u.user_id = s.user_id
                  WHERE {_FIRST('stg_sessions', 'session_id').replace('stg_sessions.', 's.')}
                    AND s.started_at >= u.created_at"""),
    ("mood_checkins", f"""INSERT INTO mood_checkins SELECT c.checkin_id, c.session_id, c.user_id, c.mood,
                  CAST(c.intensity AS INTEGER), c.created_at
                  FROM stg_mood_checkins c JOIN sessions s ON s.session_id = c.session_id
                  WHERE c.mood IN {_MOODS} AND c.intensity BETWEEN 1 AND 5
                    AND {_FIRST('stg_mood_checkins', 'checkin_id').replace('stg_mood_checkins.', 'c.')}"""),
    ("recommendations", f"""INSERT INTO recommendations SELECT r.rec_id, r.checkin_id, r.movie_id,
                  CAST(r.rank AS INTEGER), r.shown_at
                  FROM stg_recommendations r JOIN mood_checkins c ON c.checkin_id = r.checkin_id
                  JOIN movies m ON m.movie_id = r.movie_id
                  WHERE {_FIRST('stg_recommendations', 'rec_id').replace('stg_recommendations.', 'r.')}"""),
    ("ratings", f"""INSERT INTO ratings SELECT g.rating_id, g.rec_id, g.user_id, CAST(g.rating AS INTEGER), g.rated_at
                  FROM stg_ratings g JOIN recommendations rec ON rec.rec_id = g.rec_id
                  JOIN mood_checkins c ON c.checkin_id = rec.checkin_id AND c.user_id = g.user_id
                  WHERE g.rating BETWEEN 1 AND 5 AND g.rated_at >= rec.shown_at
                    AND {_FIRST('stg_ratings', 'rating_id').replace('stg_ratings.', 'g.')}"""),
]


def build_clean(conn: sqlite3.Connection) -> pd.DataFrame:
    conn.executescript(SCHEMA.read_text())
    conn.execute("PRAGMA foreign_keys = ON")
    out = []
    for table, sql in INSERTS:
        conn.execute(sql)
        staged = conn.execute(f"SELECT COUNT(*) FROM stg_{table}").fetchone()[0]
        clean = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        out.append((table, staged, clean, staged - clean, round(100 * (staged - clean) / staged, 2)))
    conn.commit()
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    assert not violations, f"Foreign-key violations in clean tables: {violations[:5]}"
    return pd.DataFrame(out, columns=["table", "staged_rows", "clean_rows", "rows_dropped", "pct_dropped"])

"""Consent, retention and deletion operations.

Design rules:
  * Deletion is a hard delete that cascades through every table holding the user's data (FK ON DELETE CASCADE).
  * The deletion log stores only a one-way hash of the user id and row counts - no personal data.
  * After restoring a backup, call reapply_deletions() so deleted users do not come back.
"""
from __future__ import annotations
import hashlib, json, sqlite3
from datetime import datetime, timedelta

_USER_TABLES = ["ratings", "recommendations", "mood_checkins", "sessions", "users"]


def _hash(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _counts_for_user(conn, user_id) -> dict[str, int]:
    q = {
        "ratings": "SELECT COUNT(*) FROM ratings WHERE user_id=?",
        "recommendations": "SELECT COUNT(*) FROM recommendations WHERE checkin_id IN (SELECT checkin_id FROM mood_checkins WHERE user_id=?)",
        "mood_checkins": "SELECT COUNT(*) FROM mood_checkins WHERE user_id=?",
        "sessions": "SELECT COUNT(*) FROM sessions WHERE user_id=?",
        "users": "SELECT COUNT(*) FROM users WHERE user_id=?",
    }
    return {t: conn.execute(sql, (user_id,)).fetchone()[0] for t, sql in q.items()}


def delete_user(conn: sqlite3.Connection, user_id: str) -> dict[str, int]:
    """Erase one user and everything derived from them. Returns rows removed per table."""
    conn.execute("PRAGMA foreign_keys = ON")
    counts = _counts_for_user(conn, user_id)
    if counts["users"] == 0:
        return counts
    conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.execute("INSERT INTO deletion_log (user_hash, action, rows_deleted, processed_at) VALUES (?,?,?,?)",
                 (_hash(user_id), "user_deletion", json.dumps(counts), _now()))
    conn.commit()
    return counts


def withdraw_consent(conn: sqlite3.Connection, user_id: str) -> None:
    """Stop using a user's data in analytics immediately (the views filter on consent_analytics)."""
    conn.execute("UPDATE users SET consent_analytics=0, consent_at=? WHERE user_id=?", (_now(), user_id))
    conn.execute("INSERT INTO deletion_log (user_hash, action, rows_deleted, processed_at) VALUES (?,?,?,?)",
                 (_hash(user_id), "consent_withdrawn", "{}", _now()))
    conn.commit()


def purge_older_than(conn: sqlite3.Connection, retention_days: int, today: datetime | None = None) -> int:
    """Retention job: delete sessions (and their check-ins/recommendations/ratings) past the retention window."""
    conn.execute("PRAGMA foreign_keys = ON")
    cutoff = ((today or datetime.now()) - timedelta(days=retention_days)).strftime("%Y-%m-%dT%H:%M:%S")
    n = conn.execute("SELECT COUNT(*) FROM sessions WHERE started_at < ?", (cutoff,)).fetchone()[0]
    conn.execute("DELETE FROM sessions WHERE started_at < ?", (cutoff,))
    conn.execute("INSERT INTO deletion_log (user_hash, action, rows_deleted, processed_at) VALUES (NULL,?,?,?)",
                 ("retention_purge", json.dumps({"sessions": n, "cutoff": cutoff}), _now()))
    conn.commit()
    return n


def reapply_deletions(conn: sqlite3.Connection) -> int:
    """After a backup restore: re-delete anyone whose deletion is recorded in the (separately kept) log."""
    hashes = {r[0] for r in conn.execute("SELECT user_hash FROM deletion_log WHERE action='user_deletion'")}
    n = 0
    for (uid,) in conn.execute("SELECT user_id FROM users").fetchall():
        if _hash(uid) in hashes:
            delete_user(conn, uid)
            n += 1
    return n

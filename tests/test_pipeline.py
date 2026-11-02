import json, sqlite3
from pathlib import Path
import pytest
from src.generate_data import generate
from src.quality_checks import load_staging, run_checks
from src.build_clean import build_clean, SCHEMA
from src.report import build_report, MIN_CELL
from src import privacy


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    raw = tmp_path_factory.mktemp("raw")
    manifest = generate(seed=7, n_users=800, out_dir=raw)
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA.read_text())
    load_staging(conn, raw)
    checks = run_checks(conn).set_index("check_id")
    clean = build_clean(conn)
    return conn, manifest, checks, clean


def test_every_injected_fault_is_detected_exactly(env):
    _, manifest, checks, _ = env
    for check_id, injected in manifest.items():
        assert checks.loc[check_id, "rows_flagged"] == injected, check_id


def test_clean_tables_have_no_integrity_problems(env):
    conn, *_ = env
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn.execute("SELECT COUNT(*) FROM ratings WHERE rating NOT BETWEEN 1 AND 5").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM (SELECT user_id FROM users GROUP BY user_id HAVING COUNT(*)>1)").fetchone()[0] == 0
    assert conn.execute("""SELECT COUNT(*) FROM ratings r JOIN recommendations x ON x.rec_id=r.rec_id
                           WHERE r.rated_at < x.shown_at""").fetchone()[0] == 0


def test_clean_rows_never_exceed_staged(env):
    *_, clean = env
    assert (clean.clean_rows <= clean.staged_rows).all()


def test_report_excludes_non_consenting_users_and_suppresses_small_cells(env):
    conn, *_ = env
    t = build_report(conn)
    consented = conn.execute("SELECT COUNT(*) FROM mood_checkins c JOIN users u USING(user_id) WHERE u.consent_analytics=1").fetchone()[0]
    assert t["headline"].mood_checkins[0] == consented
    small = t["mood_genre"][t["mood_genre"].n_ratings < MIN_CELL]
    assert small.avg_rating.isna().all()


def test_analyst_views_do_not_expose_identifiers(env):
    conn, *_ = env
    for view in ("v_checkin_facts", "v_rec_facts", "v_rating_facts"):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({view})")]
        assert "user_id" not in cols and "email_hash" not in cols


def test_delete_user_cascades_and_logs_no_personal_data(env):
    conn, *_ = env
    uid = conn.execute("SELECT user_id FROM ratings GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 1").fetchone()[0]
    counts = privacy.delete_user(conn, uid)
    assert counts["users"] == 1 and counts["ratings"] > 0
    for table in ("users", "sessions", "mood_checkins", "ratings"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id=?", (uid,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM recommendations WHERE checkin_id NOT IN (SELECT checkin_id FROM mood_checkins)").fetchone()[0] == 0
    log = conn.execute("SELECT user_hash, rows_deleted FROM deletion_log WHERE action='user_deletion'").fetchall()
    assert log and all(uid not in json.dumps(row) for row in log)


def test_withdraw_consent_removes_user_from_analytics(env):
    conn, *_ = env
    uid = conn.execute("""SELECT u.user_id FROM users u JOIN ratings r USING(user_id)
                          WHERE u.consent_analytics=1 LIMIT 1""").fetchone()[0]
    before = conn.execute("SELECT COUNT(*) FROM v_rating_facts").fetchone()[0]
    privacy.withdraw_consent(conn, uid)
    assert conn.execute("SELECT COUNT(*) FROM v_rating_facts").fetchone()[0] < before


def test_retention_purge_removes_old_sessions(env):
    conn, *_ = env
    from datetime import datetime
    removed = privacy.purge_older_than(conn, retention_days=30, today=datetime(2026, 10, 25))
    assert removed > 0
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE started_at < '2026-09-25T00:00:00'").fetchone()[0] == 0


def test_reapply_deletions_after_backup_restore(env):
    conn, *_ = env
    uid = conn.execute("SELECT user_id FROM users LIMIT 1").fetchone()[0]
    backup = sqlite3.connect(":memory:")
    conn.backup(backup)                      # snapshot taken BEFORE the deletion
    privacy.delete_user(conn, uid)
    # "restore" the old backup but keep the deletion log (stored separately in real life)
    log = conn.execute("SELECT user_hash, action, rows_deleted, processed_at FROM deletion_log").fetchall()
    backup.execute("DELETE FROM deletion_log")
    backup.executemany("INSERT INTO deletion_log (user_hash, action, rows_deleted, processed_at) VALUES (?,?,?,?)", log)
    assert backup.execute("SELECT COUNT(*) FROM users WHERE user_id=?", (uid,)).fetchone()[0] == 1
    privacy.reapply_deletions(backup)
    assert backup.execute("SELECT COUNT(*) FROM users WHERE user_id=?", (uid,)).fetchone()[0] == 0

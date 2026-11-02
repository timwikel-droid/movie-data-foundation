"""The dbt models must produce the same clean tables as the SQLite pipeline.
Skipped unless both `python run_pipeline.py` and `cd dbt && dbt build --profiles-dir .` have been run."""
import sqlite3
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
SQLITE, DUCK = ROOT / "data" / "moodbox.db", ROOT / "dbt" / "target" / "moodbox.duckdb"
duckdb = pytest.importorskip("duckdb")
pytestmark = pytest.mark.skipif(not (SQLITE.exists() and DUCK.exists()), reason="run both pipelines first")

PAIRS = [("dim_users", "users"), ("dim_movies", "movies"), ("fct_sessions", "sessions"),
         ("fct_mood_checkins", "mood_checkins"), ("fct_recommendations", "recommendations"), ("fct_ratings", "ratings")]


@pytest.mark.parametrize("dbt_table,sqlite_table", PAIRS)
def test_row_counts_match(dbt_table, sqlite_table):
    d = duckdb.connect(str(DUCK), read_only=True)
    s = sqlite3.connect(SQLITE)
    assert d.execute(f"select count(*) from {dbt_table}").fetchone()[0] == \
           s.execute(f"select count(*) from {sqlite_table}").fetchone()[0]


def test_quality_check_counts_match():
    d = duckdb.connect(str(DUCK), read_only=True)
    s = sqlite3.connect(SQLITE)
    dbt = dict(d.execute("select check_id, rows_flagged from dq_results").fetchall())
    sq = dict(s.execute("select check_id, rows_flagged from quality_issues").fetchall())
    assert dbt == sq

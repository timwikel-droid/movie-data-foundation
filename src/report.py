"""Aggregated, consent-filtered insights with small-cell suppression and explicit limitations."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd
from .utils import md_table

MIN_CELL = 10      # suppress any cell built from fewer than this many records (re-identification risk + noise)
MIN_TOP = 30       # need at least this many ratings before calling a genre the "best" for a mood

LIMITATIONS = [
    "All data is SYNTHETIC, generated with a known mood-to-genre pattern; results show the pipeline works, not how real users behave.",
    "Only users who gave analytics consent are included; if consent differs by user type, results are biased toward consenters.",
    "Ratings exist only for movies people chose to watch, so averages describe watched movies, not all recommendations (selection bias).",
    "Mood is self-reported at one moment and may be inconsistent or chosen to get a certain result; it is not a validated measure.",
    "Recommendations were shown by the system, so genre-mood links partly reflect the recommender, not independent user taste.",
    f"Cells with fewer than {MIN_CELL} ratings are suppressed; averages need at least {MIN_TOP} ratings to be called 'best'.",
    "Rows failing quality checks were dropped (see the data-quality report); if drops are not random, results could be biased.",
    "Correlation only: nothing here shows that a genre causes a mood improvement.",
]


def build_report(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    q = lambda sql: pd.read_sql(sql, conn)
    headline = q("""SELECT (SELECT COUNT(*) FROM users)                              AS users_total,
                           (SELECT COUNT(*) FROM users WHERE consent_analytics = 1)  AS users_with_consent,
                           (SELECT COUNT(*) FROM v_checkin_facts)                    AS mood_checkins,
                           (SELECT COUNT(*) FROM v_rec_facts)                        AS recommendations,
                           (SELECT COUNT(*) FROM v_rating_facts)                     AS ratings""")

    mg = q("""SELECT mood, genre, COUNT(*) AS recs, COUNT(rating) AS n_ratings, ROUND(AVG(rating), 2) AS avg_rating
              FROM v_rec_facts GROUP BY mood, genre""")
    mg = mg[mg.recs >= MIN_CELL].copy()
    mg.loc[mg.n_ratings < MIN_CELL, "avg_rating"] = float("nan")   # suppress small cells

    rank = q("""SELECT rank, COUNT(*) AS recs, COUNT(rating) AS n_ratings,
                       ROUND(100.0 * COUNT(rating) / COUNT(*), 1) AS rating_rate_pct,
                       ROUND(AVG(rating), 2) AS avg_rating
                FROM v_rec_facts GROUP BY rank ORDER BY rank""")

    ok = mg[(mg.n_ratings >= MIN_TOP)].dropna(subset=["avg_rating"])
    top = (ok.sort_values(["mood", "avg_rating"], ascending=[True, False]).groupby("mood").head(1)
             [["mood", "genre", "n_ratings", "avg_rating"]].rename(columns={"genre": "best_rated_genre"}))

    mix = q("""SELECT mood, genre, COUNT(*) AS recs FROM v_rec_facts GROUP BY mood, genre""")
    mix["share_pct"] = (100 * mix.recs / mix.groupby("mood").recs.transform("sum")).round(1)
    mix = mix[mix.recs >= MIN_CELL]
    return {"headline": headline, "mood_genre": mg, "by_rank": rank, "best_by_mood": top, "genre_mix": mix}


def write_markdown(tables: dict[str, pd.DataFrame], path: Path) -> None:
    t = tables
    md = ["# MoodBox insights report (synthetic data)\n",
          "## Scope\n", md_table(t["headline"]),
          "\n## Best-rated genre by mood\n", md_table(t["best_by_mood"]),
          "\n## Rating behaviour by recommendation rank\n", md_table(t["by_rank"]),
          "\n## Limitations\n"] + [f"- {x}" for x in LIMITATIONS]
    Path(path).write_text("\n".join(md) + "\n")

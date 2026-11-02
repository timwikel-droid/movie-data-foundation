"""Generate a SYNTHETIC MoodBox-style dataset and inject known data-quality faults.

No real MoodBox data is used. Faults are injected on purpose (and counted in a manifest) so the
quality checks can be tested: a check that cannot catch a known fault is not a useful check.
"""
from __future__ import annotations
import hashlib, itertools, json
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
RAW_DIR = Path("data/raw")
SALT = "demo-salt-store-real-salt-in-a-secret-manager"

MOODS = ["happy", "sad", "stressed", "relaxed", "excited", "bored", "nostalgic", "anxious"]
GENRES = ["comedy", "drama", "thriller", "romance", "action", "documentary", "animation", "horror", "sci-fi"]
# P(genre | mood): the "ground truth" the analysis should be able to rediscover.
_AFFINITY = {
    "happy":     [.30, .05, .05, .15, .15, .05, .20, .00, .05],
    "sad":       [.10, .30, .02, .20, .03, .10, .15, .00, .10],
    "stressed":  [.30, .05, .02, .10, .10, .13, .25, .00, .05],
    "relaxed":   [.20, .15, .05, .15, .05, .20, .10, .00, .10],
    "excited":   [.10, .02, .15, .03, .35, .00, .05, .10, .20],
    "bored":     [.15, .10, .20, .05, .20, .05, .05, .10, .10],
    "nostalgic": [.15, .25, .05, .20, .05, .10, .15, .00, .05],
    "anxious":   [.30, .10, .00, .10, .05, .15, .25, .00, .05],
}
AFFINITY = {m: np.array(w) / sum(w) for m, w in _AFFINITY.items()}
ADJ = ["Silent", "Golden", "Last", "Hidden", "Broken", "Midnight", "Crimson", "Quiet", "Electric", "Lost",
       "Paper", "Distant", "Burning", "Gentle", "Wild", "Hollow", "Bright", "Final", "Secret", "Northern"]
NOUN = ["Harbour", "Signal", "Garden", "Season", "Orbit", "Letter", "Tide", "Highway", "Lantern", "Echo",
        "Kingdom", "Winter", "Machine", "Promise", "Island", "Window", "River", "Circus", "Compass", "Story"]
TS = "%Y-%m-%dT%H:%M:%S"


def _fmt(ts: pd.Timestamp) -> str:
    return ts.strftime(TS)


def generate(seed: int = SEED, n_users: int = 1500, out_dir: Path = RAW_DIR) -> dict:
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    start, end = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-25")

    # --- movies (reference data) ---
    combos = list(itertools.product(ADJ, NOUN))
    rng.shuffle(combos)
    movies = pd.DataFrame({
        "movie_id": [f"m{i:03d}" for i in range(300)],
        "title": [f"The {a} {n}" for a, n in combos[:300]],
        "genre": rng.choice(GENRES, 300),
        "release_year": rng.integers(1980, 2026, 300),
        "runtime_min": rng.integers(80, 171, 300),
    })
    by_genre = {g: movies.loc[movies.genre == g, "movie_id"].to_numpy() for g in GENRES}
    genre_of = dict(zip(movies.movie_id, movies.genre))

    # --- users ---
    created = start + pd.to_timedelta(rng.integers(0, 260 * 86400, n_users), unit="s")
    consent = rng.random(n_users) < 0.93
    users = pd.DataFrame({
        "user_id": [f"u{i:04d}" for i in range(n_users)],
        "email_hash": [hashlib.sha256(f"user{i}@example.com{SALT}".encode()).hexdigest() for i in range(n_users)],
        "age_band": rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"], n_users, p=[.30, .35, .17, .10, .08]),
        "region": rng.choice(["NL", "Other Canada", "International"], n_users, p=[.6, .3, .1]),
        "created_at": [_fmt(t) for t in created],
        "consent_analytics": consent.astype(int),
        "consent_at": [_fmt(t) for t in created],
    })
    created_map = dict(zip(users.user_id, created))

    # --- sessions, check-ins, recommendations, ratings ---
    sessions, checkins, recs, ratings = [], [], [], []
    for uid, c_at in created_map.items():
        span = max(1, int((end - c_at).total_seconds()))
        for _ in range(1 + rng.poisson(3)):
            s_at = c_at + pd.Timedelta(seconds=int(rng.integers(0, span)))
            sid = f"s{len(sessions):06d}"
            sessions.append((sid, uid, _fmt(s_at), rng.choice(["mobile", "desktop", "tablet"], p=[.6, .3, .1])))
            if rng.random() > 0.10:  # ~10% of sessions never reach a mood check-in (a normal funnel drop-off)
                mood = rng.choice(MOODS)
                cid = f"c{len(checkins):06d}"
                c_ts = s_at + pd.Timedelta(seconds=int(rng.integers(20, 180)))
                checkins.append((cid, sid, uid, mood, int(rng.integers(1, 6)), _fmt(c_ts)))
                for rank in (1, 2, 3):
                    genre = rng.choice(GENRES, p=AFFINITY[mood])
                    mid = rng.choice(by_genre[genre])
                    rid = f"r{len(recs):06d}"
                    shown = c_ts + pd.Timedelta(seconds=int(rng.integers(1, 5)))
                    recs.append((rid, cid, mid, rank, _fmt(shown)))
                    if rng.random() < (0.45 - 0.08 * rank):  # higher-ranked picks get watched/rated more
                        w = AFFINITY[mood][GENRES.index(genre_of[mid])]
                        score = int(np.clip(round(2.6 + 4 * w + rng.normal(0, 0.9)), 1, 5))
                        r_at = shown + pd.Timedelta(seconds=int(rng.integers(3600, 3 * 86400)))
                        ratings.append((f"g{len(ratings):06d}", rid, uid, score, _fmt(r_at)))

    sessions = pd.DataFrame(sessions, columns=["session_id", "user_id", "started_at", "device"])
    checkins = pd.DataFrame(checkins, columns=["checkin_id", "session_id", "user_id", "mood", "intensity", "created_at"])
    recs = pd.DataFrame(recs, columns=["rec_id", "checkin_id", "movie_id", "rank", "shown_at"])
    ratings = pd.DataFrame(ratings, columns=["rating_id", "rec_id", "user_id", "rating", "rated_at"])
    shown_map = dict(zip(recs.rec_id, pd.to_datetime(recs.shown_at)))

    # --- inject faults (disjoint row pools so the manifest counts are exact) ---
    manifest: dict[str, int] = {}

    def pool(n):
        return list(rng.permutation(n))

    def take(p, k):
        out, p[:] = p[:k], p[k:]
        return out

    up = pool(len(users))
    dup_u = take(up, 20)
    manifest["DUP_USER_ID"] = len(dup_u)

    sp = pool(len(sessions))
    dup_s, orphan_s, early_s = take(sp, 40), take(sp, 15), take(sp, 20)
    sessions.loc[orphan_s, "user_id"] = [f"u_ghost{i}" for i in range(len(orphan_s))]
    for i in early_s:
        sessions.loc[i, "started_at"] = _fmt(created_map[sessions.loc[i, "user_id"]] - pd.Timedelta(days=3))
    manifest.update(DUP_SESSION_ID=len(dup_s), ORPHAN_SESSION_USER=len(orphan_s), SESSION_BEFORE_SIGNUP=len(early_s))

    cp = pool(len(checkins))
    miss_mood, bad_int = take(cp, 60), take(cp, 30)
    checkins["mood"] = checkins["mood"].astype(object)
    checkins.loc[miss_mood, "mood"] = None
    checkins.loc[bad_int, "intensity"] = rng.choice([0, 7], len(bad_int))
    manifest.update(MISSING_MOOD=len(miss_mood), INTENSITY_RANGE=len(bad_int))

    rp = pool(len(ratings))
    orphan_r, bad_rating, null_rating, early_r = take(rp, 25), take(rp, 10), take(rp, 10), take(rp, 35)
    ratings["rating"] = ratings["rating"].astype(float)
    ratings.loc[orphan_r, "rec_id"] = [f"r_missing{i}" for i in range(len(orphan_r))]
    ratings.loc[bad_rating, "rating"] = rng.choice([0, 6], len(bad_rating))
    ratings.loc[null_rating, "rating"] = np.nan
    for i in early_r:
        ratings.loc[i, "rated_at"] = _fmt(shown_map[ratings.loc[i, "rec_id"]] - pd.Timedelta(hours=1))
    manifest.update(ORPHAN_RATING_REC=len(orphan_r), RATING_RANGE=len(bad_rating) + len(null_rating),
                    RATING_BEFORE_SHOWN=len(early_r))

    users = pd.concat([users, users.iloc[dup_u]], ignore_index=True)
    sessions = pd.concat([sessions, sessions.iloc[dup_s]], ignore_index=True)

    for name, df in dict(users=users, movies=movies, sessions=sessions, mood_checkins=checkins,
                         recommendations=recs, ratings=ratings).items():
        df.to_csv(out_dir / f"{name}.csv", index=False)
    (out_dir / "_injected_faults.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))

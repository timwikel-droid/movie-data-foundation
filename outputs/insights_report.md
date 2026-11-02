# MoodBox insights report (synthetic data)

## Scope

| users_total | users_with_consent | mood_checkins | recommendations | ratings |
|---|---|---|---|---|
| 1500 | 1392 | 4939 | 14817 | 4226 |


## Best-rated genre by mood

| mood | best_rated_genre | n_ratings | avg_rating |
|---|---|---|---|
| anxious | comedy | 144 | 3.67 |
| bored | action | 118 | 3.48 |
| excited | action | 160 | 3.96 |
| happy | comedy | 195 | 3.77 |
| nostalgic | drama | 135 | 3.48 |
| relaxed | romance | 84 | 3.32 |
| sad | drama | 144 | 3.88 |
| stressed | comedy | 162 | 3.77 |


## Rating behaviour by recommendation rank

| rank | recs | n_ratings | rating_rate_pct | avg_rating |
|---|---|---|---|---|
| 1 | 4939 | 1802 | 36.5 | 3.27 |
| 2 | 4939 | 1380 | 27.9 | 3.27 |
| 3 | 4939 | 1044 | 21.1 | 3.32 |


## Limitations

- All data is SYNTHETIC, generated with a known mood-to-genre pattern; results show the pipeline works, not how real users behave.
- Only users who gave analytics consent are included; if consent differs by user type, results are biased toward consenters.
- Ratings exist only for movies people chose to watch, so averages describe watched movies, not all recommendations (selection bias).
- Mood is self-reported at one moment and may be inconsistent or chosen to get a certain result; it is not a validated measure.
- Recommendations were shown by the system, so genre-mood links partly reflect the recommender, not independent user taste.
- Cells with fewer than 10 ratings are suppressed; averages need at least 30 ratings to be called 'best'.
- Rows failing quality checks were dropped (see the data-quality report); if drops are not random, results could be biased.
- Correlation only: nothing here shows that a genre causes a mood improvement.

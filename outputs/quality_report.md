# Data quality report

## Checks on raw (staging) data

| check_id | table | severity | description | rows_flagged | rows_total | pct_of_table |
|---|---|---|---|---|---|---|
| DUP_USER_ID | users | error | Duplicate user_id rows | 20 | 1520 | 1.32 |
| DUP_EMAIL_HASH | users | error | Different user_ids sharing one email_hash (double sign-up) | 0 | 1520 | 0.0 |
| DUP_SESSION_ID | sessions | error | Duplicate session_id rows (double-fired tracking event) | 40 | 6022 | 0.66 |
| ORPHAN_SESSION_USER | sessions | error | Session references a user that does not exist | 15 | 6022 | 0.25 |
| SESSION_BEFORE_SIGNUP | sessions | error | Session starts before the user's sign-up time (clock/tracking error) | 20 | 6022 | 0.33 |
| ORPHAN_CHECKIN_SESSION | mood_checkins | error | Mood check-in references a missing session | 0 | 5406 | 0.0 |
| MISSING_MOOD | mood_checkins | error | Mood is missing or not in the allowed list | 60 | 5406 | 1.11 |
| INTENSITY_RANGE | mood_checkins | error | Intensity missing or outside 1-5 | 30 | 5406 | 0.55 |
| ORPHAN_REC_CHECKIN | recommendations | error | Recommendation references a missing check-in | 0 | 16218 | 0.0 |
| ORPHAN_RATING_REC | ratings | error | Rating references a recommendation that was never logged (tracking gap) | 25 | 4687 | 0.53 |
| RATING_RANGE | ratings | error | Rating missing or outside 1-5 | 20 | 4687 | 0.43 |
| RATING_BEFORE_SHOWN | ratings | error | Rating timestamped before the recommendation was shown | 35 | 4687 | 0.75 |
| RATING_USER_MISMATCH | ratings | error | Rating's user differs from the user who got the recommendation | 0 | 4687 | 0.0 |
| SESSION_NO_CHECKIN | sessions | info | Sessions with no mood check-in (funnel drop-off; monitor the rate) | 576 | 6022 | 9.56 |
| NO_ANALYTICS_CONSENT | sessions | policy | Sessions from users without analytics consent (excluded from reports) | 392 | 6022 | 6.51 |

## Staging -> clean tables

| table | staged_rows | clean_rows | rows_dropped | pct_dropped |
|---|---|---|---|---|
| movies | 300 | 300 | 0 | 0.0 |
| users | 1520 | 1500 | 20 | 1.32 |
| sessions | 6022 | 5947 | 75 | 1.25 |
| mood_checkins | 5406 | 5286 | 120 | 2.22 |
| recommendations | 16218 | 15858 | 360 | 2.22 |
| ratings | 4687 | 4501 | 186 | 3.97 |

Dropped rows include downstream records whose parent row was rejected (e.g. check-ins of a rejected session).

# Data dictionary

All data is synthetic. "Personal?" says whether the field is, or could be linked to, an identifiable person. Retention values are **proposals** to agree with MoodBox, not facts about their system.

**Classification:** `Restricted` = identifier or linkable to a person; `Sensitive` = reveals emotional state or behaviour; `Internal` = business data; `Public` = reference data.

## users
| Field | Type | Personal? | Class | Description / source | Notes |
|---|---|---|---|---|---|
| user_id | text PK | Yes (pseudonym) | Restricted | App-generated ID at sign-up | Join key; never shown to analysts |
| email_hash | text unique | Yes | Restricted | Salted SHA-256 of sign-up email | Salt lives in a secret manager, not in code. Enables duplicate-signup detection without storing emails |
| age_band | text | Indirect | Internal | Sign-up form, banded (18-24, 25-34, ...) | Banded on purpose: exact age/DOB is not needed |
| region | text | Indirect | Internal | Sign-up form (NL / Other Canada / International) | No postal code collected |
| created_at | timestamp | Yes | Internal | Sign-up time | Used to validate event ordering |
| consent_analytics | 0/1 | Yes | Internal | Consent screen | Analytics views only include rows with 1 |
| consent_at | timestamp | Yes | Internal | When consent was given/changed | Evidence of consent |

## sessions
| Field | Type | Personal? | Class | Description / source | Notes |
|---|---|---|---|---|---|
| session_id | text PK | Linkable | Sensitive | App event: session start | |
| user_id | FK users | Yes | Restricted | Owner of the session | ON DELETE CASCADE |
| started_at | timestamp | Linkable | Sensitive | Event time (UTC) | Retention clock starts here |
| device | text | No | Internal | mobile / desktop / tablet | |

## mood_checkins
| Field | Type | Personal? | Class | Description / source | Notes |
|---|---|---|---|---|---|
| checkin_id | text PK | Linkable | Sensitive | App event: mood submitted | |
| session_id, user_id | FK | Yes | Restricted | Parent session and owner | user_id duplicated here to simplify deletion and consent filtering |
| mood | text | Linkable | **Sensitive** | One of 8 fixed moods | Mood can reveal emotional state: collect only what the product needs, never use for ads/profiling without explicit consent |
| intensity | int 1-5 | Linkable | Sensitive | Self-rated strength of mood | |
| created_at | timestamp | Linkable | Sensitive | Event time | |

## recommendations
| Field | Type | Personal? | Class | Description / source | Notes |
|---|---|---|---|---|---|
| rec_id | text PK | Linkable | Sensitive | Recommender output, one row per movie shown | |
| checkin_id | FK | Linkable | Sensitive | Check-in that triggered it | ON DELETE CASCADE |
| movie_id | FK movies | No | Internal | Movie shown | |
| rank | int | No | Internal | Position in the list (1 = top) | |
| shown_at | timestamp | Linkable | Sensitive | When displayed | Used to check rating happened after display |

## ratings
| Field | Type | Personal? | Class | Description / source | Notes |
|---|---|---|---|---|---|
| rating_id | text PK | Linkable | Sensitive | App event: rating submitted | |
| rec_id | FK, unique | Linkable | Sensitive | Recommendation rated | One rating per recommendation |
| user_id | FK | Yes | Restricted | Rater | Must match the check-in's user (checked) |
| rating | int 1-5 | Linkable | Sensitive | Star rating | |
| rated_at | timestamp | Linkable | Sensitive | Event time | |

## movies
Reference data (`movie_id`, `title`, `genre`, `release_year`, `runtime_min`). Class: Public. Source: catalogue/metadata provider (check that provider's licence for redistribution and retention terms).

## Audit tables
- **quality_issues**: one row per check per run (flagged vs total). No personal data.
- **deletion_log**: one-way hash of the deleted user id, action, row counts, time. No personal data; kept separately from backups so deletions can be re-applied after a restore.

## Analyst views
`v_checkin_facts`, `v_rec_facts`, `v_rating_facts`: consent-filtered, with `user_id` and `email_hash` removed. Analysts query these, not the base tables.

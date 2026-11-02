# Survey and analytics review

**Scope:** a mock onboarding/feedback survey and the tracking events behind MoodBox's mood-to-movie flow. The questions are illustrative drafts written for this exercise, not MoodBox's actual survey. The goal is to show how I would test whether each question produces data that is clear, measurable and usable.

## 1. Question review

| # | Draft question | Problem | Revised question | Stored as |
|---|---|---|---|---|
| 1 | "How much do you love watching movies and using streaming services?" | Double-barrelled (two activities) and leading ("love") | "How often do you watch movies?" Never / Monthly / Weekly / Several times a week | `watch_frequency` (enum) |
| 2 | "How are you feeling right now?" (free text) | Unstructured; cannot be grouped or compared; invites sensitive detail | Pick one of 8 moods, then "How strong is it?" 1 (mild) to 5 (very strong) | `mood`, `intensity` |
| 3 | "Do you often watch movies when you're sad?" | "Often" is vague; yes/no hides frequency; hypothetical, not observed | Drop it: observe actual mood and viewing from the app instead of asking | derived from events |
| 4 | "Rate our amazing recommendations from 1 to 10" | Leading ("amazing"); 1-10 scale does not match the 1-5 stored in the database | "How well did this pick match your mood?" 1 (not at all) to 5 (perfectly) | `rating` (1-5) |
| 5 | "Which genres do you like?" (select any) | No "none of these"; unlimited choices give no ranking; may be skipped | "Pick up to 3 genres you watch most" plus "No preference" | `genre_pref` (up to 3) |
| 6 | "How old are you?" (number) | Collects exact age when a band is enough; typos (0, 200); raises privacy burden | Age band dropdown: 18-24, 25-34, 35-44, 45-54, 55+ | `age_band` |
| 7 | "Would you recommend MoodBox to a friend?" (shown at sign-up) | Asked before they have used the product | Ask after the 3rd session | `nps_0_10` |
| 8 | "How satisfied are you?" with labels Good / OK / Great / Bad | Scale is unordered and unbalanced | 5-point balanced scale from "Very dissatisfied" to "Very satisfied" | `satisfaction` (1-5) |

## 2. Checks applied to every question
- **One idea per question.** Split anything with "and".
- **Neutral wording.** No praise or loaded adjectives.
- **Answer options are exhaustive and mutually exclusive**, with "Prefer not to say" or "None" where relevant.
- **Scale matches storage.** The scale shown to users equals the database constraint (this project enforces 1-5 in SQL).
- **Maps to a decision.** If no product or analytics decision depends on the answer, remove the question.
- **Minimal personal data.** Ask for bands, not exact values.
- **Piloted.** Run 5 to 8 people through it aloud and watch where they hesitate; record time to complete and drop-off per question.

## 3. Tracking-plan review (events)
Each event should have a fixed name, required properties, an owner and a test.

| Event | Required properties | Failure I would test for | Check in this repo |
|---|---|---|---|
| `session_start` | session_id, user_id, timestamp, device | fires twice; user not yet created | `DUP_SESSION_ID`, `SESSION_BEFORE_SIGNUP`, `ORPHAN_SESSION_USER` |
| `mood_submitted` | checkin_id, session_id, mood, intensity | null mood; intensity outside 1-5 | `MISSING_MOOD`, `INTENSITY_RANGE` |
| `recommendation_shown` | rec_id, checkin_id, movie_id, rank | missing, so later ratings have no parent | `ORPHAN_RATING_REC` |
| `rating_submitted` | rating_id, rec_id, user_id, rating, timestamp | rating before display; wrong user; out of range | `RATING_BEFORE_SHOWN`, `RATING_USER_MISMATCH`, `RATING_RANGE` |

**Funnel monitoring:** about 10% of sessions never reach a mood check-in (`SESSION_NO_CHECKIN`). A sudden change in this rate usually means a tracking bug or a UI change, not user behaviour, so alert on movement rather than on the level.

## 4. Measures worth defining before user testing
| Measure | Definition | Caveat |
|---|---|---|
| Check-in completion rate | sessions with a mood check-in / sessions | Depends on tracking being reliable |
| Recommendation acceptance | ratings / recommendations shown, by rank | Only watched movies get rated |
| Mood-match score | mean rating (1-5) by mood and genre | Needs at least 30 ratings per cell before comparing |
| Repeat use | users with 2+ sessions in 14 days | Sensitive to when users signed up |

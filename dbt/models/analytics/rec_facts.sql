{# Consent-filtered analyst view of the data. No user_id, no email_hash. #}
select rec.rec_id, c.mood, c.intensity, m.genre, rec.rank, r.rating, u.age_band, u.region, rec.shown_at
from {{ ref('fct_recommendations') }} rec
join {{ ref('fct_mood_checkins') }} c on c.checkin_id = rec.checkin_id
join {{ ref('dim_movies') }} m        on m.movie_id   = rec.movie_id
join {{ ref('dim_users') }} u         on u.user_id    = c.user_id
left join {{ ref('fct_ratings') }} r  on r.rec_id     = rec.rec_id
where u.consent_analytics = 1

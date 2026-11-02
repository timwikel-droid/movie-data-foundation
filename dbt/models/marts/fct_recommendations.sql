select r.rec_id, r.checkin_id, r.movie_id, r.rank, r.shown_at
from {{ ref('stg_recommendations') }} r
join {{ ref('fct_mood_checkins') }} c on c.checkin_id = r.checkin_id
join {{ ref('dim_movies') }} m        on m.movie_id   = r.movie_id
where r.row_num = 1

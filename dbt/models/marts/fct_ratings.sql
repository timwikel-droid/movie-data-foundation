select g.rating_id, g.rec_id, g.user_id, g.rating, g.rated_at
from {{ ref('stg_ratings') }} g
join {{ ref('fct_recommendations') }} rec on rec.rec_id = g.rec_id
join {{ ref('fct_mood_checkins') }} c     on c.checkin_id = rec.checkin_id and c.user_id = g.user_id
where g.row_num = 1
  and g.rating between 1 and 5
  and g.rated_at >= rec.shown_at

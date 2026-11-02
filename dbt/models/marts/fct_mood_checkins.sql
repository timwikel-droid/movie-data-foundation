select c.checkin_id, c.session_id, c.user_id, c.mood, c.intensity, c.created_at
from {{ ref('stg_mood_checkins') }} c
join {{ ref('fct_sessions') }} s on s.session_id = c.session_id
where c.row_num = 1
  and c.mood in ('happy','sad','stressed','relaxed','excited','bored','nostalgic','anxious')
  and c.intensity between 1 and 5

select s.session_id, s.user_id, s.started_at, s.device
from {{ ref('stg_sessions') }} s
join {{ ref('dim_users') }} u on u.user_id = s.user_id      -- drops orphan sessions
where s.row_num = 1                                          -- drops duplicate events
  and s.started_at >= u.created_at                           -- drops sessions before sign-up

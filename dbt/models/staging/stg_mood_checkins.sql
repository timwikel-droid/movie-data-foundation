select
    checkin_id,
    session_id,
    user_id,
    mood,
    cast(intensity as int)         as intensity,
    cast(created_at as timestamp)  as created_at,
    row_number() over (partition by checkin_id order by created_at) as row_num
from {{ source('raw', 'mood_checkins') }}

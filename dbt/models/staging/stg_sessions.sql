select
    session_id,
    user_id,
    cast(started_at as timestamp) as started_at,
    device,
    row_number() over (partition by session_id order by started_at) as row_num
from {{ source('raw', 'sessions') }}

select
    rec_id,
    checkin_id,
    movie_id,
    cast(rank as int)              as rank,
    cast(shown_at as timestamp)    as shown_at,
    row_number() over (partition by rec_id order by shown_at) as row_num
from {{ source('raw', 'recommendations') }}

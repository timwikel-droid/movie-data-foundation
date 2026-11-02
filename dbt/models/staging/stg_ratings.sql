select
    rating_id,
    rec_id,
    user_id,
    cast(rating as int)            as rating,      -- NULL stays NULL; range is validated downstream
    cast(rated_at as timestamp)    as rated_at,
    row_number() over (partition by rating_id order by rated_at) as row_num
from {{ source('raw', 'ratings') }}

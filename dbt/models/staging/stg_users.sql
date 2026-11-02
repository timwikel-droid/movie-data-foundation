select
    user_id,
    email_hash,
    age_band,
    region,
    cast(created_at as timestamp)        as created_at,
    cast(consent_analytics as int)       as consent_analytics,
    cast(consent_at as timestamp)        as consent_at,
    row_number() over (partition by user_id order by created_at) as row_num   -- >1 means duplicate user_id
from {{ source('raw', 'users') }}

select user_id, email_hash, age_band, region, created_at, consent_analytics, consent_at
from {{ ref('stg_users') }}
where row_num = 1

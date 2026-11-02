{# One row per check on the RAW (staging) data. Same rules as src/quality_checks.py. #}
with
users_dedup as (
    select user_id, min(created_at) as created_at, min(consent_analytics) as consent_analytics
    from {{ ref('stg_users') }} group by user_id
),
checks as (
    select 'DUP_USER_ID' as check_id, 'users' as table_name, 'error' as severity,
           'Duplicate user_id rows' as description, count(*) as rows_flagged
    from {{ ref('stg_users') }} where row_num > 1
    union all
    select 'DUP_EMAIL_HASH', 'users', 'error', 'Different user_ids sharing one email_hash', count(*)
    from {{ ref('stg_users') }} a join {{ ref('stg_users') }} b
      on a.email_hash = b.email_hash and a.user_id < b.user_id
    union all
    select 'DUP_SESSION_ID', 'sessions', 'error', 'Duplicate session_id rows', count(*)
    from {{ ref('stg_sessions') }} where row_num > 1
    union all
    select 'ORPHAN_SESSION_USER', 'sessions', 'error', 'Session references a missing user', count(*)
    from {{ ref('stg_sessions') }} where user_id not in (select user_id from users_dedup)
    union all
    select 'SESSION_BEFORE_SIGNUP', 'sessions', 'error', 'Session starts before sign-up', count(*)
    from {{ ref('stg_sessions') }} s join users_dedup u on u.user_id = s.user_id
    where s.started_at < u.created_at
    union all
    select 'ORPHAN_CHECKIN_SESSION', 'mood_checkins', 'error', 'Check-in references a missing session', count(*)
    from {{ ref('stg_mood_checkins') }}
    where session_id not in (select session_id from {{ ref('stg_sessions') }})
    union all
    select 'MISSING_MOOD', 'mood_checkins', 'error', 'Mood missing or not in allowed list', count(*)
    from {{ ref('stg_mood_checkins') }}
    where mood is null
       or mood not in ('happy','sad','stressed','relaxed','excited','bored','nostalgic','anxious')
    union all
    select 'INTENSITY_RANGE', 'mood_checkins', 'error', 'Intensity missing or outside 1-5', count(*)
    from {{ ref('stg_mood_checkins') }} where intensity is null or intensity not between 1 and 5
    union all
    select 'ORPHAN_REC_CHECKIN', 'recommendations', 'error', 'Recommendation references a missing check-in', count(*)
    from {{ ref('stg_recommendations') }}
    where checkin_id not in (select checkin_id from {{ ref('stg_mood_checkins') }})
    union all
    select 'ORPHAN_RATING_REC', 'ratings', 'error', 'Rating references a recommendation never logged', count(*)
    from {{ ref('stg_ratings') }}
    where rec_id not in (select rec_id from {{ ref('stg_recommendations') }})
    union all
    select 'RATING_RANGE', 'ratings', 'error', 'Rating missing or outside 1-5', count(*)
    from {{ ref('stg_ratings') }} where rating is null or rating not between 1 and 5
    union all
    select 'RATING_BEFORE_SHOWN', 'ratings', 'error', 'Rating timestamped before recommendation shown', count(*)
    from {{ ref('stg_ratings') }} r join {{ ref('stg_recommendations') }} rec on rec.rec_id = r.rec_id
    where r.rated_at < rec.shown_at
    union all
    select 'RATING_USER_MISMATCH', 'ratings', 'error', 'Rating user differs from check-in user', count(*)
    from {{ ref('stg_ratings') }} r
    join {{ ref('stg_recommendations') }} rec on rec.rec_id = r.rec_id
    join {{ ref('stg_mood_checkins') }} c on c.checkin_id = rec.checkin_id
    where c.user_id <> r.user_id
    union all
    select 'SESSION_NO_CHECKIN', 'sessions', 'info', 'Sessions with no mood check-in (funnel drop-off)',
           count(distinct session_id)
    from {{ ref('stg_sessions') }}
    where session_id not in (select session_id from {{ ref('stg_mood_checkins') }})
    union all
    select 'NO_ANALYTICS_CONSENT', 'sessions', 'policy', 'Sessions from users without analytics consent',
           count(distinct s.session_id)
    from {{ ref('stg_sessions') }} s join users_dedup u on u.user_id = s.user_id
    where u.consent_analytics = 0
),
totals as (
    select 'users' as table_name, count(*) as rows_total from {{ ref('stg_users') }}
    union all select 'sessions', count(*) from {{ ref('stg_sessions') }}
    union all select 'mood_checkins', count(*) from {{ ref('stg_mood_checkins') }}
    union all select 'recommendations', count(*) from {{ ref('stg_recommendations') }}
    union all select 'ratings', count(*) from {{ ref('stg_ratings') }}
)
select c.check_id, c.table_name, c.severity, c.description, c.rows_flagged, t.rows_total,
       round(100.0 * c.rows_flagged / t.rows_total, 2) as pct_of_table
from checks c join totals t on t.table_name = c.table_name

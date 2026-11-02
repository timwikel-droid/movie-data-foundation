-- Fails if any clean rating is timestamped before its recommendation was shown.
select g.rating_id
from {{ ref('fct_ratings') }} g
join {{ ref('fct_recommendations') }} r on r.rec_id = g.rec_id
where g.rated_at < r.shown_at

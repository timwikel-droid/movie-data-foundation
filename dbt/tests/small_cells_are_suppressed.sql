-- Fails if any aggregate shows an average built from fewer ratings than the minimum cell size.
select mood, genre
from {{ ref('mood_genre_summary') }}
where avg_rating is not null and n_ratings < {{ var('min_cell') }}

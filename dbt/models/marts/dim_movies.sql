select movie_id, title, genre, release_year, runtime_min
from {{ ref('stg_movies') }}

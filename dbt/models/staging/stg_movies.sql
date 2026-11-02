select
    movie_id,
    title,
    genre,
    cast(release_year as int) as release_year,
    cast(runtime_min as int)  as runtime_min
from {{ source('raw', 'movies') }}

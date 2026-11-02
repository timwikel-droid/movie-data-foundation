{# Aggregates with small-cell suppression. Cells below var('min_cell') ratings show NULL averages. #}
select
    mood,
    genre,
    count(*)        as recs,
    count(rating)   as n_ratings,
    case when count(rating) >= {{ var('min_cell') }} then round(avg(rating), 2) end as avg_rating
from {{ ref('rec_facts') }}
group by mood, genre
having count(*) >= {{ var('min_cell') }}

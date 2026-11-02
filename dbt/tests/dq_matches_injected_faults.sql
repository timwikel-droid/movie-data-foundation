{{ config(tags=['synthetic_only']) }}
-- Synthetic-data ground truth: every injected fault must be detected with the exact count.
select e.check_id, e.expected_rows, d.rows_flagged
from {{ ref('expected_faults') }} e
left join {{ ref('dq_results') }} d on d.check_id = e.check_id
where d.rows_flagged is null or d.rows_flagged <> e.expected_rows

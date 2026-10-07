-- Recompute the /stats aggregates after a bulk import.
--   psql -d pyq -f scripts/refresh-question-stats.sql
refresh materialized view question_stats;

analyze question_stats;
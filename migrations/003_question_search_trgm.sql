-- These indexes accelerate the leading-wildcard ILIKE predicates in /questions.
-- CREATE INDEX CONCURRENTLY keeps reads and writes available during the build.
create extension if not exists pg_trgm;

create index concurrently if not exists questions_chapter_trgm_idx
  on questions using gin (chapter gin_trgm_ops);
create index concurrently if not exists questions_topic_trgm_idx
  on questions using gin (topic gin_trgm_ops);
create index concurrently if not exists questions_paper_title_trgm_idx
  on questions using gin (paper_title gin_trgm_ops);
create index concurrently if not exists questions_exam_trgm_idx
  on questions using gin (exam gin_trgm_ops);
create index concurrently if not exists questions_exam_group_trgm_idx
  on questions using gin (exam_group gin_trgm_ops);

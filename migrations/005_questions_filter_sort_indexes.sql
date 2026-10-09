-- Restore the question filter and ordering indexes used by /questions and
-- chapter catalog queries.
-- Concurrent builds keep normal reads and writes available.
create index concurrently if not exists questions_subject_idx
  on questions(subject);
create index concurrently if not exists questions_chapter_idx
  on questions(chapter);
create index concurrently if not exists questions_topic_idx
  on questions(topic);
create index concurrently if not exists questions_year_idx
  on questions(year);
create index concurrently if not exists questions_difficulty_idx
  on questions(difficulty);
create index concurrently if not exists questions_type_idx
  on questions(type);
create index concurrently if not exists questions_chapter_group_idx
  on questions(chapter_group);
create index concurrently if not exists questions_subject_chapter_idx
  on questions(subject, chapter);
create index concurrently if not exists questions_year_date_id_idx
  on questions(year desc, exam_date desc nulls last, id desc);

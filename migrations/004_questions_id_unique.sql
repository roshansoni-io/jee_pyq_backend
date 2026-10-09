-- Restore the primary-key lookup path when questions.id is not indexed.
-- The ID column is already NOT NULL; this unique index also enforces uniqueness.
create unique index concurrently if not exists questions_id_unique_idx
  on questions(id);

-- Remove only exact duplicate chapter and embedding records, then enforce the
-- keys declared in schema.sql. The runner rechecks earlier migrations after
-- this cleanup so migration 001 can add its taxonomy constraints immediately.
delete from chapters duplicate
using chapters keeper
where duplicate.subject_id = keeper.subject_id
  and duplicate.id = keeper.id
  and duplicate.ctid > keeper.ctid;

delete from question_embeddings duplicate
using question_embeddings keeper
where duplicate.question_id = keeper.question_id
  and duplicate.ctid > keeper.ctid;

delete from topics duplicate
using topics keeper
where duplicate.chapter_id = keeper.chapter_id
  and duplicate.id = keeper.id
  and duplicate.ctid > keeper.ctid;

create unique index concurrently if not exists chapters_id_unique_idx
  on chapters(id);
create unique index concurrently if not exists question_embeddings_question_id_unique_idx
  on question_embeddings(question_id);
create unique index concurrently if not exists topics_chapter_id_id_unique_idx
  on topics(chapter_id, id);

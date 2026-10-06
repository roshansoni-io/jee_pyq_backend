create extension if not exists vector;

create table if not exists subjects (
  id text primary key
);

create table if not exists chapters (
  id text primary key,
  subject_id text not null references subjects(id),
  chapter_group text,
  name text not null default ''
);

create table if not exists topics (
  chapter_id text not null references chapters(id) on delete cascade,
  id text not null,
  primary key (chapter_id, id)
);

create table if not exists questions (
  id text primary key,
  exam text not null default '',
  exam_group text not null default '',
  subject text not null references subjects(id),
  chapter text not null references chapters(id),
  chapter_group text,
  year integer not null default 0,
  paper_title text not null default '',
  difficulty text not null default '',
  topic text not null default '',
  type text not null default '',
  exam_date date,
  answer jsonb,
  question text not null default '',
  options jsonb not null default '[]'::jsonb,
  correct_options jsonb not null default '[]'::jsonb,
  explanation text not null default '',
  is_out_of_syllabus boolean not null default false,
  is_bonus boolean not null default false,
  is_img_question boolean not null default false,
  is_img_explanation boolean not null default false,
  is_img_option jsonb not null default '[]'::jsonb
);

create table if not exists question_embeddings (
  question_id text primary key references questions(id) on delete cascade,
  embedding vector(384)
);

create index if not exists questions_subject_idx on questions(subject);
create index if not exists questions_chapter_idx on questions(chapter);
create index if not exists questions_topic_idx on questions(topic);
create index if not exists questions_year_idx on questions(year);
create index if not exists questions_difficulty_idx on questions(difficulty);
create index if not exists questions_type_idx on questions(type);
create index if not exists questions_chapter_group_idx on questions(chapter_group);
create index if not exists question_embeddings_embedding_idx
  on question_embeddings using hnsw (embedding vector_cosine_ops);

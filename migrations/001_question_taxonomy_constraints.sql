-- Apply once to databases created before the taxonomy foreign keys were added.
begin;

alter table chapters
  add constraint chapters_subject_id_id_key unique (subject_id, id);

-- Empty string is the stored topic sentinel for questions without a topic.
insert into topics (chapter_id, id)
select id, '' from chapters
on conflict (chapter_id, id) do nothing;

alter table questions
  add constraint questions_subject_chapter_fk
    foreign key (subject, chapter) references chapters(subject_id, id),
  add constraint questions_chapter_topic_fk
    foreign key (chapter, topic) references topics(chapter_id, id);

commit;

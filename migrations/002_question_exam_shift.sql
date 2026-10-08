-- Add normalized exam date and shift values for existing question rows.
begin;

alter table questions add column if not exists shift text;

update questions
set shift = case
  when paper_title ~* 'morning (slot|shift)|shift *(1|i)([^i]|$)' then 'Shift 1'
  when paper_title ~* 'evening (slot|shift)|shift *(2|ii)([^i]|$)' then 'Shift 2'
  else null
end,
exam_date = coalesce(
  exam_date,
  to_date(
    regexp_replace(
      paper_title,
      '^.*([0-9]{4}) [(]Online[)] ([0-9]{1,2})(st|nd|rd|th) ([A-Za-z]+).*$',
      '\2 \4 \1'
    ),
    'DD FMMonth YYYY'
  )
)
where paper_title ~* '[0-9]{4} [(]Online[)] [0-9]{1,2}(st|nd|rd|th) [A-Za-z]+';

commit;

# JEE PYQ API Reference (v1)

Base URL: `/api/v1`
All requests/responses are JSON (`Content-Type: application/json`). JSON keys are `snake_case`.

Run with:

```bash
python3 -m app
```

At startup, the API applies pending SQL files from `migrations/` before opening the
request connection pool. See [`DATABASE_STRUCTURE.md`](DATABASE_STRUCTURE.md) for the
schema and current external-database snapshot.

Interactive docs: http://localhost:8000/docs

## Response envelope

Success:

```json
{
  "data": "...",
  "meta": {}
}
```

`meta` is optional and carries pagination, totals, or filters.

Error:

```json
{
  "error": {"code": "not_found", "message": "question not found"}
}
```

The HTTP status carries the transport-level status. `error.code` is a stable
machine-readable application code and is not a copy of that status. Current codes
include `bad_request`, `not_found`, `method_not_allowed`, `validation_error`,
`http_error`, and `internal_error`. Validation errors may include a `details` array
with input locations and messages; internal errors never expose exception details.

## Object shapes

### Subject

```json
{"id": "physics", "name": "Physics"}
```

### Chapter

```json
{"id": "thermodynamics", "name": "Thermodynamics", "chapter_number": 12, "group": "Mechanics", "question_count": 95}
```

`chapter_number` is a continuous order within its subject, based on the NCERT Class XI
then Class XII textbook sequence. It is an order for this question-bank taxonomy, not
the printed chapter number of a single NCERT book, because several bank chapters split
or combine textbook chapters. Chapter results are ordered by `chapter_number`.

`name` is the id title-cased (`jee`/`ac`/`dc` stay upper, minor words stay lower after
the first). Chapters are ordered by `chapter_number` within each subject.

`question_count` comes from a grouped subquery over `questions` (see
`questions_subject_chapter_idx` in schema.sql).

### Topic

```json
{"id": "laws-of-thermodynamics", "name": "Laws of Thermodynamics"}
```

### Question Summary

Used in list responses.

```json
{
  "id": "abc123",
  "exam": "JEE Main",
  "exam_group": "JEE",
  "subject": "physics",
  "chapter": "thermodynamics",
  "year": 2023,
  "exam_date": "2023-04-10",
  "shift": "Shift 1",
  "paper_title": "JEE Main 2023 (Online) 10th April Morning Shift",
  "difficulty": "medium",
  "topic": {"id": "laws-of-thermodynamics", "name": "Laws of Thermodynamics"},
  "type": "mcq"
}
```

`exam` and `exam_group` are title-cased from their stored slugs. `subject` and
`chapter` are raw slugs; `topic` is an object with a raw `id` slug and display `name`,
or `null`. `exam_date` is an ISO date or `null`; `shift` is `Shift 1`,
`Shift 2`, or `null`. The year, date, and shift are independent fields. Existing
morning/evening slot labels are normalized to shifts 1 and 2.

### Full Question

Used in single-question responses. Question Summary plus:

```json
{
  "is_bonus": false,
  "type": "integer",
  "question": "<p>...</p>",
  "options": [{"identifier": "A", "content": "..."}],
  "correct_options": [],
  "answer": null,
  "explanation": "<p>...</p>"
}
```

`answer` is `null` for all questions in the current imported dataset. The sibling
`../jee_mains_pyqs.json` and imported pickle cache both have 3,263 integer questions
with `answer: null` and `correct_options: []`. Their explanations may show a result,
but the API does not infer an answer by parsing explanation text. Seven MCQs also
have empty `correct_options`.

`<img>` tags are inlined in `question`, `explanation` and `options[].content`, so no
separate image flags are returned.

## Endpoints

### GET /api/v1/health

```json
{"data": {"status": "ok", "questions": 14973, "chapters": 91}}
```

Counts the raw `questions` and `chapters` rows on every call. The external database
now has 91 chapter rows after duplicate cleanup.

### GET /api/v1/stats

```json
{
  "data": {
    "total_questions": 14973,
    "total_subjects": 3,
    "total_chapters": 91,
    "by_subject": [{"id": "physics", "count": 5097}],
    "by_year": [{"year": 2023, "count": 2112}]
  }
}
```

Reads the `question_stats` materialized view, so counts are as of its last refresh. Run
`psql -d pyq -f scripts/refresh-question-stats.sql` after a bulk import. If the view is
missing, aggregates are computed live instead. The external view needs refreshing
after the chapter duplicate cleanup to report the corrected chapter count.

### GET /api/v1/subjects

```json
{"data": [{"id": "physics", "name": "Physics"}]}
```

### GET /api/v1/subjects/{subject_id}/chapters

Chapter breakdown within a subject, each carrying its `question_count`.

Query parameters:

| param  | type | default | description                        |
| ------ | ---- | ------- | ---------------------------------- |
| limit  | int | 100     | page size, clamped to [0, 500]     |
| offset | int | 0       | clamped to >= 0                    |

```json
{
  "data": [
    {"id": "units-and-measurements", "name": "Units and Measurements", "chapter_number": 1, "group": "Mechanics", "question_count": 120}
  ],
  "meta": {"subject": "physics", "total": 28, "limit": 100, "offset": 0}
}
```

Each chapter has a `chapter_number` and a `group` such as `Mechanics` or `Physical
Chemistry`. Duplicate chapter rows are collapsed by chapter ID, and `total` counts
distinct IDs in the subject.

Unknown subject → `404` envelope. A subject that exists but has no chapters returns
`data: []` with `total: 0`, not a 404.

### GET /api/v1/chapters/{chapter_id}

```json
{
  "data": {
    "id": "thermodynamics",
    "name": "Thermodynamics",
    "chapter_number": 12,
    "group": "Mechanics",
    "question_count": 95,
    "topics": [
      {"id": "laws-of-thermodynamics", "name": "Laws of Thermodynamics"}
    ]
  }
}
```

Unknown chapter → `404` envelope.

### GET /api/v1/questions

Query parameters:

| param      | type   | default | description                              |
| ---------- | ------ | ------- | ---------------------------------------- |
| subject    | string | —       | filter by subject id                     |
| chapter    | string | —       | filter by chapter id                     |
| topic      | string | —       | filter by topic id                       |
| group      | string | —       | filter by chapter group (e.g. `physical-chemistry`) |
| difficulty | string | —       | filter by difficulty                     |
| year       | int    | —       | filter by year                           |
| type       | string | —       | filter by question type                  |
| q          | string | —       | case-insensitive substring across `chapter`, `topic`, `paper_title`, `exam`, `exam_group` |
| limit      | int    | 50      | page size, clamped to [0, 500]           |
| offset     | int    | 0       | clamped to >= 0                          |
| sort       | string | newest  | `newest`, `oldest`, or `random`          |
| seed       | string | —       | pins `random` order across pages         |

Non-numeric `limit`/`offset` fall back to the default rather than erroring.
`year` must be an integer; invalid values return a `400` error envelope.

Response:

```json
{
  "data": [{"id": "abc123", "...": "..."}],
  "meta": {"total": 1234, "limit": 50, "offset": 0, "sort": "newest", "filters": {"subject": "physics"}}
}
```

Invalid `sort` → `400` envelope.

### GET /api/v1/questions/{question_id}

```json
{
  "data": {
    "id": "abc123",
    "type": "integer",
    "topic": {"id": "thermodynamics", "name": "Thermodynamics"},
    "question": "<p>...</p>"
  }
}
```

Unknown id → `404` envelope.
`data.topic` is `null` when the question has no topic. The question's `type` remains in
`data` for both list and single-question responses. Pagination responses omit
`has_more`; clients can derive it from `total`, `offset`, and the number of returned items.

The cluster handler exists in the codebase but is not registered on the API router, so
`/api/v1/cluster` is not currently available.

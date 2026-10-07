# JEE PYQ API Reference (v1)

Base URL: `/api/v1`
All requests/responses are JSON (`Content-Type: application/json`). JSON keys are `snake_case`.

Run with:

```bash
python3 -m app
```

Interactive docs: http://localhost:8000/docs

## Response envelope

Success:

```json
{
  "data": "...",
  "meta": {}
}
```

`meta` is optional and carries pagination, totals, filters, or clustering metadata.

Error:

```json
{
  "error": {"code": 404, "message": "Question not found"}
}
```

## Object shapes

### Subject

```json
{"id": "physics", "name": "Physics"}
```

### Chapter

```json
{"id": "thermodynamics", "name": "Thermodynamics", "question_count": 95}
```

`name` is the id title-cased (`jee`/`ac`/`dc` stay upper, minor words stay lower after
the first). Chapters are ordered by chapter group, then by id.

`question_count` comes from a grouped subquery over `questions` (see
`questions_subject_chapter_idx` in schema.sql).

### Topic

```json
{"id": "laws-of-thermodynamics", "name": "Laws of Thermodynamics", "question_count": 15}
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
  "paper_title": "JEE Main 2023 Session 1",
  "difficulty": "medium",
  "topic": "laws-of-thermodynamics",
  "type": "mcq"
}
```

`exam` and `exam_group` are title-cased from their stored slugs. `subject`, `chapter` and
`topic` are raw slugs.

### Full Question

Used in single-question and practice responses. Question Summary plus:

```json
{
  "is_bonus": false,
  "question": "<p>...</p>",
  "options": [{"identifier": "A", "content": "..."}],
  "correct_options": [0],
  "answer": "42",
  "explanation": "<p>...</p>"
}
```

Integer-type questions carry the answer as a string in `answer` and have empty `correct_options`.

`<img>` tags are inlined in `question`, `explanation` and `options[].content`, so no
separate image flags are returned.

## Endpoints

### GET /api/v1/health

```json
{"data": {"status": "ok", "questions": 14973, "chapters": 91}}
```

Counts both tables on every call, so it reflects the database as it is rather than import
state.

### GET /api/v1/stats

```json
{
  "data": {
    "total_questions": 14973,
    "total_subjects": 3,
    "total_chapters": 91,
    "by_subject": [{"id": "physics", "count": 5097}],
    "by_year": [{"year": 2023, "count": 1200}]
  }
}
```

Reads the `question_stats` materialized view, so counts are as-of the last refresh. Run
`psql -d pyq -f scripts/refresh-question-stats.sql` after a bulk import. If the view is
missing, the aggregates are computed live instead.

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
    {"id": "kinematics", "name": "Kinematics", "question_count": 120}
  ],
  "meta": {"subject": "physics", "total": 28, "limit": 100, "offset": 0, "has_more": false}
}
```

Chapters are ordered by chapter group, then by id. `total` counts every chapter in the
subject, so `has_more` is correct across pages.

Unknown subject → `404` envelope. A subject that exists but has no chapters returns
`data: []` with `total: 0`, not a 404.

### GET /api/v1/chapters/{chapter_id}/topics

```json
{"data": [{"id": "laws-of-thermodynamics", "name": "Laws of Thermodynamics", "question_count": 15}], "meta": {"chapter": "thermodynamics"}}
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

Response:

```json
{
  "data": [{"id": "abc123", "...": "..."}],
  "meta": {"total": 1234, "limit": 50, "offset": 0, "has_more": true, "sort": "newest", "filters": {"subject": "physics"}}
}
```

Invalid `sort` → `400` envelope.

### GET /api/v1/questions/{question_id}

```json
{"data": {"id": "abc123", "question": "<p>...</p>", "...": "..."}}
```

Unknown id → `404` envelope.

### GET /api/v1/practice

Same filters as `/questions`, plus:

| param     | type   | default | description                                          |
| --------- | ------ | ------- | ---------------------------------------------------- |
| limit     | int    | 10      | page size, clamped to [0, 500]                       |
| order     | string | random  | `newest`, `oldest`, or `random`; invalid falls back to `random` |
| seed      | string | —       | pins `random` order across pages                     |
| question  | string | —       | anchor question id, returned first                   |

Returns Full Questions. `meta.total` is the number of rows returned; `meta.available` is
the size of the filtered set, and `has_more` compares against it.

```json
{"data": [{"id": "abc123", "...": "..."}], "meta": {"total": 10, "available": 95, "offset": 0, "has_more": true, "order": "random", "filters": {"chapter": "thermodynamics"}}}
```

`question` fills the page with siblings of that question and sets `meta.anchored: true`.
It is looked up subject to the same filters, so an id from a different chapter or subject
is ignored and the ordinary page is returned instead. `offset` addresses this sequence:
the anchor occupies position 0 and siblings follow, so pages advance under a `seed`.
`limit=0` returns an empty page rather than just the anchor.

### GET /api/v1/cluster

Query parameters:

| param         | type   | default | description                 |
| ------------- | ------ | ------- | --------------------------- |
| subject       | string | —       | filter by subject           |
| chapter       | string | —       | filter by chapter           |
| topic         | string | —       | filter by topic             |
| group         | string | —       | filter by chapter group     |
| difficulty    | string | —       | filter by difficulty        |
| type          | string | —       | filter by question type     |
| year          | int    | —       | filter by year              |
| q             | string | —       | substring search, as `/questions` |
| threshold     | float  | 0.6     | cosine similarity threshold |
| max_questions | int    | 2000    | clamped to [0, 20000]       |

Clusters questions by cosine similarity, greedily: each vector joins the nearest existing
cluster whose centroid clears `threshold`, otherwise it starts a new one. Centroid
similarity uses raw dot products, so only vectors from `question_embeddings` are
clustered; ids without one are returned in `missing_embedding`. `q` and `max_questions`
take the same non-numeric fallback as `/questions`.

```json
{
  "data": {
    "clusters": [
      {"cluster_id": 0, "size": 15, "representative_question_id": "q_001", "question_ids": ["q_001", "q_002"]}
    ],
    "missing_embedding": ["q_004"]
  },
  "meta": {"num_clusters": 5, "threshold": 0.6}
}
```

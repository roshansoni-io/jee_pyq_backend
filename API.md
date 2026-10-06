# JEE PYQ API Reference (v1)

Base URL: `/api/v1`
All requests/responses are JSON (`Content-Type: application/json`). JSON keys are `snake_case`.

Run with:

```bash
python -m api.app
```

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
{"id": "physics", "name": "Physics", "chapter_count": 28, "question_count": 5097}
```

### Chapter

```json
{"id": "thermodynamics", "name": "Thermodynamics", "question_count": 95, "topic_count": 12}
```

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
  "chapter_group": "mechanics",
  "year": 2023,
  "paper_title": "JEE Main 2023 Session 1",
  "difficulty": "medium",
  "topic": "laws-of-thermodynamics",
  "type": "mcq",
  "exam_date": "2023-01-25",
  "is_out_of_syllabus": false,
  "is_bonus": false
}
```

### Full Question

Used in single-question and practice responses. Question Summary plus:

```json
{
  "question": "<p>...</p>",
  "options": [{"identifier": "A", "content": "..."}],
  "correct_options": [0],
  "answer": "42",
  "explanation": "<p>...</p>",
  "is_img_question": false,
  "is_img_explanation": false,
  "is_img_option": false
}
```

Integer-type questions carry the answer as a string in `answer` and have empty `correct_options`.

## Endpoints

### GET /api/v1/health

```json
{"data": {"status": "ok", "questions": 14973, "chapters": 91}}
```

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

### GET /api/v1/subjects

```json
{"data": [{"id": "physics", "name": "Physics", "chapter_count": 28, "question_count": 5097}]}
```

### GET /api/v1/subjects/{subject_id}/groups

Chapter-group breakdown within a subject (e.g. `physical-chemistry`, `organic-chemistry`, `inorganic-chemistry` under chemistry).

```json
{"data": [{"id": "physical-chemistry", "name": "Physical Chemistry", "question_count": 1761}], "meta": {"subject": "chemistry"}}
```

### GET /api/v1/subjects/{subject_id}/chapters

```json
{
  "data": [{"id": "kinematics", "name": "Kinematics", "question_count": 120, "topic_count": 8}],
  "meta": {"subject": "physics"}
}
```

Unknown subject → `404` envelope.

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
| limit      | int    | 50      | page size, clamped to [0, 500]           |
| offset     | int    | 0       | clamped to >= 0                          |
| sort       | string | newest  | `newest`, `oldest`, or `random`          |

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

Same filters as `/questions`; `limit` defaults to 10 and is clamped to [0, 50]. Returns Full Questions in random order.

```json
{"data": [{"id": "abc123", "...": "..."}], "meta": {"total": 10, "filters": {"chapter": "thermodynamics"}}}
```

### GET /api/v1/cluster

Query parameters:

| param         | type  | default | description                 |
| ------------- | ----- | ------- | --------------------------- |
| chapter       | string| —       | filter by chapter           |
| subject       | string| —       | filter by subject           |
| topic         | string| —       | filter by topic             |
| group         | string| —       | filter by chapter group     |
| year          | int   | —       | filter by year              |
| threshold     | float | 0.6     | cosine similarity threshold |
| max_questions | int   | 2000    | clamped to [0, 20000]       |

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

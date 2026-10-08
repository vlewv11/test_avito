# Async RPC Contract: Review Moderation

## Interaction Flow
1. Client calls synchronous RPC `SubmitModerationTask`.
2. Service validates payload and immediately returns task acceptance with `status=IN_PROGRESS`.
3. Task is enqueued for async processing.
4. After processing finishes, service emits `moderation.task.completed` event to internal data bus.
5. Client fetches result via synchronous RPC `GetModerationTaskResult`.

## RPC: SubmitModerationTask

### Request
Only two top-level fields are allowed.

```json
{
  "request_id": "req-8f0c2c1d",
  "review": {
    "review_id": "rvw-1001",
    "text": "Доставили быстро, но упаковка повреждена",
    "rating": 3,
    "images": [
      {
        "url": "https://cdn.example/reviews/1001/1.jpg",
        "mime_type": "image/jpeg"
      }
    ]
  }
}
```

### Request Rules
- Top-level: exactly `request_id`, `review`.
- `request_id` is idempotency key for submit.
- `review.review_id` and `review.text` are required.
- `review.rating` is optional (`1..5`).
- `review.images` is optional array (`maxItems=10`).
- Image object supports either `url` or `base64` (at least one required), plus optional `mime_type`.

### Response
```json
{
  "task_id": "tsk-cf7b74",
  "status": "IN_PROGRESS",
  "accepted_at": "2026-06-02T11:20:41Z"
}
```

## RPC: GetModerationTaskResult

### Request
```json
{
  "task_id": "tsk-cf7b74"
}
```

### Response: processing
```json
{
  "task_id": "tsk-cf7b74",
  "status": "QUEUED"
}
```

### Response: completed
```json
{
  "task_id": "tsk-cf7b74",
  "status": "COMPLETED",
  "decision": "REVIEW",
  "primary_reason_code": "PII_PHONE",
  "secondary_reason_codes": ["PII_EMAIL"],
  "topic_results": [
    {
      "topic_id": "02_pii",
      "decision": "REVIEW",
      "reason_codes": ["PII_PHONE", "PII_EMAIL"],
      "confidence": 0.93
    }
  ],
  "finished_at": "2026-06-02T11:20:44Z"
}
```

### Response: failed
```json
{
  "task_id": "tsk-cf7b74",
  "status": "FAILED",
  "error_code": "INTERNAL_ERROR",
  "error_message": "Worker processing failed"
}
```

## Event Contract
Event name: `moderation.task.completed`.

```json
{
  "task_id": "tsk-cf7b74",
  "request_id": "req-8f0c2c1d",
  "status": "COMPLETED",
  "result_version": 1,
  "decision": "REVIEW",
  "primary_reason_code": "PII_PHONE",
  "secondary_reason_codes": ["PII_EMAIL"],
  "topic_results": [
    {
      "topic_id": "02_pii",
      "decision": "REVIEW",
      "reason_codes": ["PII_PHONE", "PII_EMAIL"],
      "confidence": 0.93
    }
  ],
  "finished_at": "2026-06-02T11:20:44Z"
}
```

Delivery semantics: at-least-once. Consumers must deduplicate by `(task_id, result_version)`.

## Task State Machine
`QUEUED -> IN_PROGRESS -> COMPLETED | FAILED | EXPIRED`

- `SubmitModerationTask` always returns `IN_PROGRESS` for accepted input.
- `GetModerationTaskResult` returns current state.
- Final states are immutable for a given `(task_id, result_version)`.

## Error Model
- Validation errors: malformed payload, missing fields, invalid ranges.
- Not found: unknown `task_id`.
- Internal errors: processing/storage failures.

Recommended error payload for RPC-level failures:

```json
{
  "error_code": "INVALID_REQUEST",
  "message": "request_id is required",
  "details": ["field=request_id"]
}
```

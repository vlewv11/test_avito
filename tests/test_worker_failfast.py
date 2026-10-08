from __future__ import annotations

import asyncio
from typing import Any

from service import main as service_main


def test_finish_task_later_marks_task_failed_and_emits_failed_event(monkeypatch: Any) -> None:
    async def _run() -> None:
        events: list[dict[str, Any]] = []
        app = service_main.create_app(event_publisher=events.append, processing_delay=0.0)
        task_id = "tsk-failfast-1"

        async with app["tasks_lock"]:
            app["tasks"][task_id] = {
                "task_id": task_id,
                "request_id": "req-failfast-1",
                "review": {"review_id": "rvw-fail", "text": "hello"},
                "status": "IN_PROGRESS",
                "accepted_at": service_main.now_iso(),
                "result": None,
            }

        def _boom(_: dict[str, Any], __: Any) -> dict[str, Any]:
            raise RuntimeError("Worker processing failed")

        monkeypatch.setattr(service_main, "classify_review", _boom)
        await service_main.finish_task_later(app, task_id)

        async with app["tasks_lock"]:
            task = app["tasks"][task_id]
            result = task["result"]

        assert task["status"] == "FAILED"
        assert result["status"] == "FAILED"
        assert result["error_code"] == "INTERNAL_ERROR"
        assert result["error_message"] == "Worker processing failed"
        assert "finished_at" in result

        assert len(events) == 1
        event = events[0]
        assert event["task_id"] == task_id
        assert event["request_id"] == "req-failfast-1"
        assert event["status"] == "FAILED"
        assert event["result_version"] == 1
        assert event["error_code"] == "INTERNAL_ERROR"
        assert event["error_message"] == "Worker processing failed"
        assert "finished_at" in event

    asyncio.run(_run())

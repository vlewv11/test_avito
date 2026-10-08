#!/usr/bin/env python3
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from aiohttp import web

from service.moderation_engine import classify_review
from service.ml_topic_inference import load_ml_ensemble


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_publish_event(event: dict[str, Any]) -> None:
    # Stub publisher: in a real service this is sent to Kafka/NATS/etc.
    print(json.dumps({"event_name": "moderation.task.completed", "payload": event}, ensure_ascii=False), flush=True)


def invalid_request(message: str, details: list[str]) -> web.Response:
    return web.json_response(
        {
            "error_code": "INVALID_REQUEST",
            "message": message,
            "details": details,
        },
        status=400,
    )


def validate_submit_payload(payload: Any) -> tuple[bool, web.Response | None]:
    if not isinstance(payload, dict):
        return False, invalid_request("payload must be an object", ["field=body"])

    required_top_level = {"request_id", "review"}
    if set(payload.keys()) != required_top_level:
        return False, invalid_request(
            "top-level fields must be exactly request_id and review",
            ["field=request_id", "field=review"],
        )

    if not isinstance(payload.get("request_id"), str) or not payload["request_id"].strip():
        return False, invalid_request("request_id is required", ["field=request_id"])

    review = payload.get("review")
    if not isinstance(review, dict):
        return False, invalid_request("review is required", ["field=review"])

    if not isinstance(review.get("review_id"), str) or not review["review_id"].strip():
        return False, invalid_request("review_id is required", ["field=review.review_id"])

    if not isinstance(review.get("text"), str) or not review["text"].strip():
        return False, invalid_request("text is required", ["field=review.text"])

    return True, None


def validate_get_result_payload(payload: Any) -> tuple[bool, web.Response | None]:
    if not isinstance(payload, dict):
        return False, invalid_request("payload must be an object", ["field=body"])

    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        return False, invalid_request("task_id is required", ["field=task_id"])

    return True, None


async def finish_task_later(app: web.Application, task_id: str) -> None:
    await asyncio.sleep(app["processing_delay"])
    try:
        async with app["tasks_lock"]:
            task = app["tasks"].get(task_id)
            if not task:
                return

            classification = classify_review(task["review"], app["ml_ensemble"])
            
            finished_at = now_iso()
            task["status"] = "COMPLETED"
            task["result"] = {
                "task_id": task_id,
                "status": "COMPLETED",
                "decision": classification["decision"],
                "primary_reason_code": classification["primary_reason_code"],
                "secondary_reason_codes": classification["secondary_reason_codes"],
                "topic_results": classification["topic_results"],
                "finished_at": finished_at,
            }
            event = {
                "task_id": task_id,
                "request_id": task["request_id"],
                "status": "COMPLETED",
                "result_version": 1,
                "decision": classification["decision"],
                "primary_reason_code": classification["primary_reason_code"],
                "secondary_reason_codes": classification["secondary_reason_codes"],
                "topic_results": classification["topic_results"],
                "finished_at": finished_at,
            }
    except Exception as exc:
        logging.exception("Background worker failed for task_id=%s", task_id)
        async with app["tasks_lock"]:
            task = app["tasks"].get(task_id)
            if not task:
                return
            finished_at = now_iso()
            error_message = str(exc)[:2000] or "Worker processing failed"
            task["status"] = "FAILED"
            task["result"] = {
                "task_id": task_id,
                "status": "FAILED",
                "error_code": "INTERNAL_ERROR",
                "error_message": error_message,
                "finished_at": finished_at,
            }
            event = {
                "task_id": task_id,
                "request_id": task["request_id"],
                "status": "FAILED",
                "result_version": 1,
                "error_code": "INTERNAL_ERROR",
                "error_message": error_message,
                "finished_at": finished_at,
            }

    app["event_publisher"](event)


async def handle_submit(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except Exception:
        return invalid_request("invalid json", ["field=body"])

    ok, response = validate_submit_payload(payload)
    if not ok and response is not None:
        return response

    task_id = f"tsk-{uuid.uuid4().hex[:8]}"

    async with request.app["tasks_lock"]:
        request.app["tasks"][task_id] = {
            "task_id": task_id,
            "request_id": payload["request_id"],
            "review": payload["review"],
            "status": "IN_PROGRESS",
            "accepted_at": now_iso(),
            "result": None,
        }
        accepted_at = request.app["tasks"][task_id]["accepted_at"]

    asyncio.create_task(finish_task_later(request.app, task_id))

    return web.json_response(
        {
            "task_id": task_id,
            "status": "IN_PROGRESS",
            "accepted_at": accepted_at,
        }
    )


async def handle_get_result(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except Exception:
        return invalid_request("invalid json", ["field=body"])

    ok, response = validate_get_result_payload(payload)
    if not ok and response is not None:
        return response

    task_id = payload["task_id"]

    async with request.app["tasks_lock"]:
        task = request.app["tasks"].get(task_id)
        if not task:
            return web.json_response({"error": "task_not_found", "task_id": task_id}, status=404)

        if task["result"] is None:
            return web.json_response({"task_id": task_id, "status": "IN_PROGRESS"})

        return web.json_response(task["result"])


async def handle_not_found(_: web.Request) -> web.Response:
    return web.json_response({"error": "not_found"}, status=404)


def create_app(
    event_publisher: Callable[[dict[str, Any]], None] | None = None,
    processing_delay: float = 1.0,
    ml_manifest_path: str | None = None,
) -> web.Application:
    app = web.Application()
    app["tasks"] = {}
    app["tasks_lock"] = asyncio.Lock()
    app["event_publisher"] = event_publisher or default_publish_event
    app["processing_delay"] = processing_delay
    app["ml_ensemble"] = load_ml_ensemble(ml_manifest_path)

    app.router.add_post("/rpc/SubmitModerationTask", handle_submit)
    app.router.add_post("/rpc/GetModerationTaskResult", handle_get_result)
    app.router.add_route("*", "/{tail:.*}", handle_not_found)
    return app


def main() -> None:
    host = "127.0.0.1"
    port = 8080
    print(f"Moderation skeleton is running on http://{host}:{port}", flush=True)
    web.run_app(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()

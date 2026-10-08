from __future__ import annotations

import asyncio
from typing import Any

import pytest
from aiohttp.test_utils import TestClient, TestServer

from service.main import create_app
from tests.scenario_data import all_cases


async def run_case(case: dict[str, Any]) -> None:
    emitted_events: list[dict[str, Any]] = []
    app = create_app(event_publisher=emitted_events.append, processing_delay=0.01)

    async with TestServer(app) as server:
        async with TestClient(server) as client:
            submit_resp = await client.post("/rpc/SubmitModerationTask", json=case["review"])
            assert submit_resp.status == 200
            submit_payload = await submit_resp.json()
            assert submit_payload["status"] == "IN_PROGRESS"

            task_id = submit_payload["task_id"]
            for _ in range(60):
                result_resp = await client.post("/rpc/GetModerationTaskResult", json={"task_id": task_id})
                assert result_resp.status == 200
                result_payload = await result_resp.json()
                if result_payload["status"] == "COMPLETED":
                    break
                await asyncio.sleep(0.01)
            else:
                raise AssertionError(f"task {task_id} did not complete")

            assert result_payload["decision"] == case["expected_decision"]
            assert result_payload["primary_reason_code"] == case["expected_primary_reason_code"]
            for code in case["expected_secondary_reason_codes"]:
                assert code in result_payload["secondary_reason_codes"]

            assert len(emitted_events) == 1
            event = emitted_events[0]
            assert event["task_id"] == task_id
            assert event["status"] == "COMPLETED"
            assert event["decision"] == result_payload["decision"]
            assert event["primary_reason_code"] == result_payload["primary_reason_code"]
            assert event["secondary_reason_codes"] == result_payload["secondary_reason_codes"]
            assert event["topic_results"] == result_payload["topic_results"]


@pytest.mark.parametrize("case", all_cases, ids=[case["case_id"] for case in all_cases])
def test_e2e_cases(case: dict[str, Any]) -> None:
    asyncio.run(run_case(case))


def test_submit_invalid_payload() -> None:
    async def _run() -> None:
        app = create_app(processing_delay=0.01)
        async with TestServer(app) as server:
            async with TestClient(server) as client:
                response = await client.post(
                    "/rpc/SubmitModerationTask",
                    json={"request_id": "req-bad", "review": {"review_id": "r1"}},
                )
                assert response.status == 400
                payload = await response.json()
                assert payload["error_code"] == "INVALID_REQUEST"

                response = await client.post(
                    "/rpc/SubmitModerationTask",
                    json={"request_id": "req-bad", "review": {"review_id": "r1", "text": "ok"}, "extra": 1},
                )
                assert response.status == 400

    asyncio.run(_run())


def test_get_result_invalid_or_missing_task() -> None:
    async def _run() -> None:
        app = create_app(processing_delay=0.01)
        async with TestServer(app) as server:
            async with TestClient(server) as client:
                bad_response = await client.post("/rpc/GetModerationTaskResult", json={})
                assert bad_response.status == 400
                bad_payload = await bad_response.json()
                assert bad_payload["error_code"] == "INVALID_REQUEST"

                not_found = await client.post(
                    "/rpc/GetModerationTaskResult",
                    json={"task_id": "tsk-unknown"},
                )
                assert not_found.status == 404
                not_found_payload = await not_found.json()
                assert not_found_payload["error"] == "task_not_found"

    asyncio.run(_run())


def test_regression_sexual_slur_is_rejected() -> None:
    async def _run() -> None:
        app = create_app(processing_delay=0.01)
        async with TestServer(app) as server:
            async with TestClient(server) as client:
                submit = await client.post(
                    "/rpc/SubmitModerationTask",
                    json={
                        "request_id": "req-regression-1",
                        "review": {
                            "review_id": "rvw-regression-1",
                            "text": "шлюхи москвы",
                            "rating": 5,
                        },
                    },
                )
                assert submit.status == 200
                task_id = (await submit.json())["task_id"]

                for _ in range(60):
                    result = await client.post("/rpc/GetModerationTaskResult", json={"task_id": task_id})
                    payload = await result.json()
                    if payload.get("status") == "COMPLETED":
                        break
                    await asyncio.sleep(0.01)
                else:
                    raise AssertionError("task did not complete")

                assert payload["decision"] == "REJECT"
                assert payload["primary_reason_code"] == "ADULT_SEXUAL_TEXT"

    asyncio.run(_run())

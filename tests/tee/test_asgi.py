import asyncio
import logging
import uuid
from pathlib import Path

import pytest

from structlog_config import configure_logger, tee_logs
from tests.utils import read_jsonl


def test_asgi_capture_includes_streaming_background_work_and_request_errors(tmp_path: Path):
    """Exercise the README ASGI pattern with concurrent HTTP scopes, streaming,

    awaited framework background work, exception logging before closure, and non-HTTP pass-through.
    """
    responses = pytest.importorskip("starlette.responses")
    background = pytest.importorskip("starlette.background")
    log_dir = tmp_path / "requests"
    log_dir.mkdir()

    log = configure_logger(json_logger=True)

    class ScopedLogTeeMiddleware:
        def __init__(self, app, log_dir: Path):
            self.app = app
            self.log_dir = log_dir

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            request_id = str(uuid.uuid4())
            log_path = self.log_dir / f"{request_id}.jsonl"
            with log.context(request_id=request_id), tee_logs(log_path):
                log.info("request started", path=scope.get("path"))
                try:
                    await self.app(scope, receive, send)
                except Exception:
                    log.exception("unhandled error in request")
                    raise
                finally:
                    log.info("request finished")

    async def run_asgi_scenarios():
        # Scenario A: Streaming response with background work
        sent_messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent_messages.append(message)

        async def streaming_app(scope, receive, send):
            async def chunks():
                log.info("streaming_chunk_1")
                yield b"first chunk"
                assert sent_messages[-1]["body"] == b"first chunk"
                log.info("streaming_chunk_2")
                yield b"second chunk"

            async def bg_task():
                assert sent_messages[-1]["more_body"] is False
                logging.getLogger("response.background").info(
                    "background_processing_done"
                )

            response = responses.StreamingResponse(
                chunks(), background=background.BackgroundTask(bg_task)
            )
            await response(scope, receive, send)

        wrapped_stream = ScopedLogTeeMiddleware(streaming_app, log_dir)
        await wrapped_stream(
            {"type": "http", "path": "/stream", "asgi": {"spec_version": "2.4"}},
            receive,
            send,
        )
        assert sent_messages[0]["type"] == "http.response.start"
        assert sent_messages[0]["status"] == 200
        assert [message["body"] for message in sent_messages[1:]] == [
            b"first chunk", b"second chunk", b""
        ]
        assert [message["more_body"] for message in sent_messages[1:]] == [
            True, True, False
        ]

        # Scenario B: Exception in application
        async def error_app(scope, receive, send):
            log.info("about_to_crash")
            raise ValueError("simulated crash in handler")

        wrapped_err = ScopedLogTeeMiddleware(error_app, log_dir)
        with pytest.raises(ValueError, match="simulated crash in handler"):
            await wrapped_err({"type": "http", "path": "/crash"}, None, None)

        # Scenario C: Non-HTTP scope pass-through (e.g. websocket or lifespan)
        non_http_logged = False

        async def lifespan_app(scope, receive, send):
            nonlocal non_http_logged
            non_http_logged = True
            log.info("lifespan_event")

        wrapped_lifespan = ScopedLogTeeMiddleware(lifespan_app, log_dir)
        await wrapped_lifespan({"type": "lifespan"}, None, None)
        assert non_http_logged

        # Scenario D: Concurrent HTTP requests
        async def concurrent_app(scope, receive, send):
            route = scope.get("path")
            log.info("handling_route", route=route)
            await asyncio.sleep(0.01)
            log.info("done_route", route=route)

        wrapped_concurrent = ScopedLogTeeMiddleware(concurrent_app, log_dir)
        await asyncio.gather(
            wrapped_concurrent({"type": "http", "path": "/req1"}, None, None),
            wrapped_concurrent({"type": "http", "path": "/req2"}, None, None),
        )

    asyncio.run(run_asgi_scenarios())

    log_files = list(log_dir.glob("*.jsonl"))
    # 1 streaming + 1 error + 2 concurrent = 4 HTTP requests total. Lifespan created 0 files.
    assert len(log_files) == 4

    # Streaming file checks
    stream_files = [
        f for f in log_files if "streaming_chunk_1" in f.read_text(encoding="utf-8")
    ]
    assert len(stream_files) == 1
    stream_entries = read_jsonl(stream_files[0].read_text(encoding="utf-8"))
    events = [e["event"] for e in stream_entries]
    assert events == [
        "request started",
        "streaming_chunk_1",
        "streaming_chunk_2",
        "background_processing_done",
        "request finished",
    ]

    # Error file checks
    error_files = [
        f for f in log_files if "about_to_crash" in f.read_text(encoding="utf-8")
    ]
    assert len(error_files) == 1
    error_entries = read_jsonl(error_files[0].read_text(encoding="utf-8"))
    err_events = [e["event"] for e in error_entries]
    assert "request started" in err_events
    assert "about_to_crash" in err_events
    assert "unhandled error in request" in err_events
    assert "request finished" in err_events
    exc_record = next(
        e for e in error_entries if e["event"] == "unhandled error in request"
    )
    assert "exception" in exc_record
    assert "simulated crash in handler" in str(exc_record["exception"])

    # Concurrent files checks
    req1_files = [f for f in log_files if "/req1" in f.read_text(encoding="utf-8")]
    req2_files = [f for f in log_files if "/req2" in f.read_text(encoding="utf-8")]
    assert len(req1_files) == 1
    assert len(req2_files) == 1
    assert req1_files[0] != req2_files[0]
    assert "/req2" not in req1_files[0].read_text(encoding="utf-8")
    assert "/req1" not in req2_files[0].read_text(encoding="utf-8")

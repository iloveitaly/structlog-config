import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import StreamingResponse

from structlog_config import configure_logger, tee_logs
from tests.utils import read_jsonl


def test_asgi_capture_includes_streaming_background_work_and_request_errors(
    tmp_path: Path,
):
    """
    Exercise ASGI request teeing with a FastAPI server.

    Covers streaming, background work, errors, and concurrency.
    """

    log_dir = tmp_path / "requests"
    log_dir.mkdir()

    log = configure_logger(json_logger=True, enable_tee=True)

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

    lifespan_ran = False

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal lifespan_ran
        lifespan_ran = True
        log.info("lifespan_event")
        yield

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(ScopedLogTeeMiddleware, log_dir=log_dir)

    @app.get("/stream")
    def stream_route(background_tasks: BackgroundTasks):
        def bg_task():
            logging.getLogger("response.background").info(
                "background_processing_done"
            )

        background_tasks.add_task(bg_task)

        async def chunks():
            log.info("streaming_chunk_1")
            yield b"first chunk"
            log.info("streaming_chunk_2")
            yield b"second chunk"

        return StreamingResponse(chunks())

    @app.get("/crash")
    def crash_route():
        log.info("about_to_crash")
        raise ValueError("simulated crash in handler")

    @app.get("/req1")
    async def req1():
        log.info("handling_route", route="/req1")
        await asyncio.sleep(0.01)
        log.info("done_route", route="/req1")
        return {"ok": 1}

    @app.get("/req2")
    async def req2():
        log.info("handling_route", route="/req2")
        await asyncio.sleep(0.01)
        log.info("done_route", route="/req2")
        return {"ok": 2}

    async def run_scenarios():
        # non-HTTP lifespan scope passes through without creating request capture files
        lifespan_messages = [
            {"type": "lifespan.startup"},
            {"type": "lifespan.shutdown"},
        ]

        async def lifespan_receive():
            return lifespan_messages.pop(0)

        async def lifespan_send(message):
            pass

        await app(
            {"type": "lifespan", "asgi": {"version": "3.0"}},
            lifespan_receive,
            lifespan_send,
        )
        assert lifespan_ran

        transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # streaming response with background task
            stream_response = await client.get("/stream")
            assert stream_response.status_code == 200
            assert stream_response.content == b"first chunksecond chunk"

            # exception in request handler
            with pytest.raises(ValueError, match="simulated crash in handler"):
                await client.get("/crash")

            # concurrent HTTP requests
            res1, res2 = await asyncio.gather(
                client.get("/req1"),
                client.get("/req2"),
            )
            assert res1.status_code == 200
            assert res2.status_code == 200

    asyncio.run(run_scenarios())

    log_files = list(log_dir.glob("*.jsonl"))
    # 1 streaming + 1 error + 2 concurrent = 4 HTTP requests total; lifespan created 0 files
    assert len(log_files) == 4

    # streaming file checks
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

    # error file checks
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

    # concurrent files checks
    req1_files = [f for f in log_files if "/req1" in f.read_text(encoding="utf-8")]
    req2_files = [f for f in log_files if "/req2" in f.read_text(encoding="utf-8")]
    assert len(req1_files) == 1
    assert len(req2_files) == 1
    assert req1_files[0] != req2_files[0]
    assert "/req2" not in req1_files[0].read_text(encoding="utf-8")
    assert "/req1" not in req2_files[0].read_text(encoding="utf-8")

import asyncio
import contextvars
import io
import logging
import threading
from pathlib import Path

import pytest
import structlog

from structlog_config import configure_logger, tee_logs
from tests.capture_utils import CaptureStreams


@pytest.mark.parametrize("json_logger", [False, True])
def test_child_task_retains_sink_but_stops_capture_when_parent_scope_exits(json_logger):
    from structlog_config.tee import _ACTIVE_SINKS

    with io.StringIO() as target, CaptureStreams() as capture:
        log = configure_logger(json_logger=json_logger)
        stdlib_log = logging.getLogger("inherited_child")

        async def run_test():
            child_logged = asyncio.Event()
            parent_exited = asyncio.Event()

            async def child():
                assert _ACTIVE_SINKS.get()[0] is sink
                log.info("child inside scope")
                stdlib_log.warning("stdlib inside scope")
                child_logged.set()
                await parent_exited.wait()
                assert _ACTIVE_SINKS.get()[0] is sink
                assert sink.file is None
                log.info("child outside scope")
                stdlib_log.warning("stdlib outside scope")

            with tee_logs(target):
                sink = _ACTIVE_SINKS.get()[0]
                task = asyncio.create_task(child())
                await child_logged.wait()

            assert _ACTIVE_SINKS.get() == ()
            parent_exited.set()
            await task

        asyncio.run(asyncio.wait_for(run_test(), timeout=5))
        assert not target.closed
        assert "child inside scope" in target.getvalue()
        assert "stdlib inside scope" in target.getvalue()
        assert "outside scope" not in target.getvalue()
        assert "child outside scope" in capture.stdout.getvalue()
        assert "stdlib outside scope" in capture.stdout.getvalue()


def test_cancellation_closes_sink_and_restores_outer_scope(tmp_path: Path):
    primary = io.StringIO()
    log = configure_logger(logger_factory=structlog.PrintLoggerFactory(file=primary))
    outer_path = tmp_path / "outer.log"
    inner_path = tmp_path / "inner.log"

    async def run_test():
        entered = asyncio.Event()
        blocked = asyncio.Event()

        async def request():
            with tee_logs(outer_path):
                try:
                    with tee_logs(inner_path):
                        log.info("request running")
                        entered.set()
                        try:
                            await blocked.wait()
                        finally:
                            log.info("request cancellation cleanup")
                except asyncio.CancelledError:
                    log.info("outer scope restored")
                    raise

        task = asyncio.create_task(request())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        log.info("after cancellation")

    asyncio.run(asyncio.wait_for(run_test(), timeout=5))
    inner_text = inner_path.read_text()
    outer_text = outer_path.read_text()
    assert "request running" in inner_text
    assert "request cancellation cleanup" in inner_text
    assert "outer scope restored" not in inner_text
    assert "outer scope restored" in outer_text
    assert "after cancellation" not in outer_text
    assert "after cancellation" in primary.getvalue()


def test_concurrent_requests_keep_shared_logger_output_isolated(
    tmp_path: Path,
):
    """Interleave requests A/B and an unscoped task, all using identical shared

    structlog and stdlib logger instances. Assert exact file event sets/counts and no leakage;
    primary receives all events once.
    """
    file_a = tmp_path / "req_a.log"
    file_b = tmp_path / "req_b.log"

    with CaptureStreams() as capture:
        log = configure_logger()
        stdlib_log = logging.getLogger("shared_stdlib")

        step_barrier = threading.Barrier(3)
        done_barrier = threading.Barrier(4)
        errors: list[Exception] = []

        def request_a():
            try:
                with tee_logs(file_a):
                    log.info("req_a_step1")
                    step_barrier.wait(timeout=5.0)
                    stdlib_log.info("req_a_step2")
                    step_barrier.wait(timeout=5.0)
                    log.info("req_a_step3")
            except Exception as e:  # noqa: BLE001
                errors.append(e)
            finally:
                done_barrier.wait(timeout=5.0)

        def request_b():
            try:
                with tee_logs(file_b):
                    log.info("req_b_step1")
                    step_barrier.wait(timeout=5.0)
                    stdlib_log.info("req_b_step2")
                    step_barrier.wait(timeout=5.0)
                    log.info("req_b_step3")
            except Exception as e:  # noqa: BLE001
                errors.append(e)
            finally:
                done_barrier.wait(timeout=5.0)

        def unscoped_task():
            try:
                log.info("unscoped_step1")
                step_barrier.wait(timeout=5.0)
                stdlib_log.info("unscoped_step2")
                step_barrier.wait(timeout=5.0)
                log.info("unscoped_step3")
            except Exception as e:  # noqa: BLE001
                errors.append(e)
            finally:
                done_barrier.wait(timeout=5.0)

        threads = [
            threading.Thread(target=request_a, daemon=True),
            threading.Thread(target=request_b, daemon=True),
            threading.Thread(target=unscoped_task, daemon=True),
        ]
        try:
            for t in threads:
                t.start()
            done_barrier.wait(timeout=5.0)
        finally:
            step_barrier.abort()
            done_barrier.abort()

        for t in threads:
            t.join(timeout=2.0)

        assert not errors, f"Errors in concurrent workers: {errors}"

        text_a = file_a.read_text(encoding="utf-8")
        text_b = file_b.read_text(encoding="utf-8")
        primary = capture.stdout.getvalue()

        # File A checks: exact set of events for request A
        assert "req_a_step1" in text_a
        assert "req_a_step2" in text_a
        assert "req_a_step3" in text_a
        assert "req_b" not in text_a
        assert "unscoped" not in text_a
        lines_a = [line for line in text_a.splitlines() if line.strip()]
        assert len(lines_a) == 3

        # File B checks: exact set of events for request B
        assert "req_b_step1" in text_b
        assert "req_b_step2" in text_b
        assert "req_b_step3" in text_b
        assert "req_a" not in text_b
        assert "unscoped" not in text_b
        lines_b = [line for line in text_b.splitlines() if line.strip()]
        assert len(lines_b) == 3

        # Primary output receives all events exactly once
        for prefix in ["req_a", "req_b", "unscoped"]:
            for step in ["step1", "step2", "step3"]:
                event_name = f"{prefix}_{step}"
                assert event_name in primary
                assert primary.count(event_name) == 1


def test_capture_follows_inherited_task_and_executor_contexts(tmp_path: Path):
    """Test child tasks created in scope, tasks created beforehand,

    awaited async logger methods, asyncio.to_thread, explicit copy_context executor work,
    and an explicitly empty-context negative case.
    """
    scope_file = tmp_path / "async_tasks.log"

    async def run_test():
        log = configure_logger()
        pre_started = asyncio.Event()
        pre_allow_log = asyncio.Event()
        pre_done = asyncio.Event()

        async def pre_created_worker():
            pre_started.set()
            await pre_allow_log.wait()
            log.info("pre_created_event")
            pre_done.set()

        # Task created beforehand (before entering scope)
        pre_task = asyncio.create_task(pre_created_worker())
        await pre_started.wait()

        with tee_logs(scope_file):
            # 1. Child task created in scope inherits context
            async def in_scope_child():
                log.info("in_scope_child_event")

            child_task = asyncio.create_task(in_scope_child())
            await child_task

            # 2. Awaited async logger method
            await log.ainfo("awaited_ainfo_event")

            # 3. asyncio.to_thread propagates context
            def thread_fn():
                log.info("to_thread_event")

            await asyncio.to_thread(thread_fn)

            # 4. Explicit copy_context in executor propagates context
            def copy_ctx_fn():
                log.info("copy_ctx_event")

            ctx = contextvars.copy_context()
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, ctx.run, copy_ctx_fn)

            # 5. Explicitly empty context negative case
            def empty_ctx_fn():
                log.info("empty_ctx_event")

            empty_ctx = contextvars.Context()
            await loop.run_in_executor(None, empty_ctx.run, empty_ctx_fn)

            # Release pre-created task while scope is active
            pre_allow_log.set()
            await pre_done.wait()
            await pre_task

    asyncio.run(run_test())

    content = scope_file.read_text(encoding="utf-8")
    assert "in_scope_child_event" in content
    assert "awaited_ainfo_event" in content
    assert "to_thread_event" in content
    assert "copy_ctx_event" in content

    # Pre-created task and empty-context executor work must NOT reach mirror
    assert "pre_created_event" not in content
    assert "empty_ctx_event" not in content


def test_scope_closure_stops_inherited_and_concurrent_writers(
    tmp_path: Path,
):
    """Let a child outlive its parent using deterministic synchronization.

    Its later log must reach primary only, without closed-file errors or file growth.
    Exercise simultaneous sink writes/closure and verify complete records.
    """
    scope_file = tmp_path / "child_outlives.log"

    with CaptureStreams() as capture:
        log = configure_logger()
        child_entered = threading.Event()
        parent_exited = threading.Event()
        child_finished = threading.Event()
        worker_errors: list[Exception] = []

        def long_lived_child():
            try:
                log.info("child_while_open")
                child_entered.set()
                assert parent_exited.wait(timeout=5.0)
                # Emitted after parent exited scope and closed sink
                log.info("child_after_parent_closed")
            except Exception as e:  # noqa: BLE001
                worker_errors.append(e)
            finally:
                child_finished.set()

        with tee_logs(scope_file):
            ctx = contextvars.copy_context()
            t = threading.Thread(target=ctx.run, args=(long_lived_child,), daemon=True)
            t.start()
            assert child_entered.wait(timeout=5.0)

        # Parent exited scope; sink is now closed
        parent_exited.set()
        assert child_finished.wait(timeout=5.0)
        t.join(timeout=2.0)

    assert not worker_errors
    file_text = scope_file.read_text(encoding="utf-8")
    primary_text = capture.stdout.getvalue()

    assert "child_while_open" in file_text
    assert "child_after_parent_closed" not in file_text
    assert "child_while_open" in primary_text
    assert "child_after_parent_closed" in primary_text

    # Simultaneous sink writes and closure stress test
    stress_file = tmp_path / "stress_closure.log"
    stress_workers = 4
    stop_workers = threading.Event()
    stress_errors: list[Exception] = []

    def hammering_worker():
        try:
            while not stop_workers.is_set():
                log.info("hammer_event", tid=threading.get_ident())
        except Exception as e:  # noqa: BLE001
            stress_errors.append(e)

    with tee_logs(stress_file):
        threads = [
            threading.Thread(
                target=contextvars.copy_context().run,
                args=(hammering_worker,),
                daemon=True,
            )
            for _ in range(stress_workers)
        ]
        for t in threads:
            t.start()
        threading.Event().wait(0.05)
        # Exiting scope closes sink under lock while threads are hammering

    stop_workers.set()
    for t in threads:
        t.join(timeout=2.0)

    assert not stress_errors
    lines = [
        l for l in stress_file.read_text(encoding="utf-8").splitlines() if l.strip()
    ]
    assert len(lines) > 0
    for line in lines:
        assert "hammer_event" in line


def test_nested_scopes_restore_capture_after_errors_and_context_clear(
    tmp_path: Path,
):
    """Test nested scopes, exception cleanup, restoration,

    and log.clear not changing tee state. No sink remains active after a failing request.
    """
    outer_file = tmp_path / "outer.log"
    inner_file = tmp_path / "inner.log"

    log = configure_logger()

    # 1. Nested scopes
    with tee_logs(outer_file):
        log.info("outer_1")
        with tee_logs(inner_file):
            log.info("inner_both")
        log.info("outer_2")

    outer_text = outer_file.read_text(encoding="utf-8")
    inner_text = inner_file.read_text(encoding="utf-8")

    assert "outer_1" in outer_text
    assert "inner_both" in outer_text
    assert "outer_2" in outer_text

    assert "inner_both" in inner_text
    assert "outer_1" not in inner_text
    assert "outer_2" not in inner_text

    # 2. Exception cleanup & restoration
    fail_file = tmp_path / "fail.log"
    with (
        pytest.raises(RuntimeError, match="deliberate_failure"),
        tee_logs(fail_file),
    ):
        log.info("before_failure")
        raise RuntimeError("deliberate_failure")

    assert "before_failure" in fail_file.read_text(encoding="utf-8")

    # Verify no sink remains active in this context
    from structlog_config.tee import _ACTIVE_SINKS

    assert _ACTIVE_SINKS.get() == ()

    log.info("after_failed_scope")
    assert "after_failed_scope" not in fail_file.read_text(encoding="utf-8")

    # 3. log.clear() does not disable tee capture
    clear_file = tmp_path / "clear.log"
    with tee_logs(clear_file):
        log.local(request_id="req-999")
        log.info("event_with_context")
        log.clear()  # clears structlog contextvars, must not clear tee sinks
        log.info("event_after_clear")

    clear_text = clear_file.read_text(encoding="utf-8")
    assert "event_with_context" in clear_text
    assert "req-999" in clear_text
    assert "event_after_clear" in clear_text
    assert "req-999" not in clear_text.split("event_after_clear")[1]

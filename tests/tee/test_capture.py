import contextvars
import io
import logging
import sys
import warnings
from pathlib import Path
from unittest import mock

import pytest
import structlog
from structlog import DropEvent

from structlog_config import configure_logger, get_logger, tee_logs
from tests.capture_utils import CaptureStreams
from tests.utils import read_jsonl, temp_env_var


def test_inactive_and_closed_scopes_do_not_encode_text(tmp_path: Path):
    primary = io.StringIO()
    log = configure_logger(logger_factory=structlog.PrintLoggerFactory(file=primary))
    stdlib_log = logging.getLogger("surrogate_text")
    # surrogateescape maps undecodable byte 0xff to U+DCFF, which strict UTF-8 rejects
    message = b"filename \xff".decode("utf-8", errors="surrogateescape")

    log.info(message)
    stdlib_log.warning(message)

    target = tmp_path / "closed.log"
    with tee_logs(target):
        inherited_context = contextvars.copy_context()

    inherited_context.run(log.info, message)
    inherited_context.run(stdlib_log.warning, message)

    assert primary.getvalue().count(message) == 4
    assert target.read_bytes() == b""


@pytest.mark.parametrize("json_logger", [False, True])
@pytest.mark.parametrize("destination", ["stringio", "bytesio", "text_file", "binary_file"])
def test_caller_owned_streams_capture_both_logging_stacks_without_closing(
    tmp_path: Path, json_logger: bool, destination: str
):
    """
    Preserve rendered records and caller ownership across text and binary streams.

    Use seek(0) and read() because all four test destinations support them, unlike
    getvalue(), which is specific to the in-memory buffers. Only the test needs
    readable, seekable streams; tee_logs itself writes and flushes without seeking.

    U+00E9 (e with an acute accent) takes two bytes when encoded as UTF-8.
    It catches accidental ASCII encoding or incorrect decoding of JSON bytes
    into text streams, which ASCII-only messages would not reveal. Exact output
    comparisons also detect changed bytes or corrupted characters.
    """
    if destination == "stringio":
        target = io.StringIO()
    elif destination == "bytesio":
        target = io.BytesIO()
    elif destination == "text_file":
        target = (tmp_path / "capture.log").open("w+", encoding="utf-8")
    else:
        target = (tmp_path / "capture.log").open("w+b")

    with target, CaptureStreams() as capture:
        log = configure_logger(json_logger=json_logger)
        stdlib_log = logging.getLogger("stream_capture")
        is_text = isinstance(target, io.TextIOBase)
        prefix = "existing content\n"
        target.write(prefix if is_text else prefix.encode("utf-8"))

        with tee_logs(target):
            # the capture helper stores text and binary output separately, so read each record
            capture.stdout.clear()
            log.info("structured caf\u00e9", count=1)
            expected = prefix + capture.stdout.getvalue()
            capture.stdout.clear()
            stdlib_log.warning("stdlib caf\u00e9")
            expected += capture.stdout.getvalue()
            if destination in ("text_file", "binary_file"):
                assert (tmp_path / "capture.log").read_bytes() == expected.encode("utf-8")
            target.seek(0)
            contents = target.read()
            assert contents == (expected if is_text else expected.encode("utf-8"))

        assert not target.closed
        log.info("outside capture")
        stdlib_log.warning("outside stdlib capture")
        target.seek(0)
        assert target.read() == contents

        text = contents if is_text else contents.decode("utf-8")
        if json_logger:
            assert [entry["event"] for entry in read_jsonl(text[len(prefix):])] == [
                "structured caf\u00e9", "stdlib caf\u00e9"
            ]


@pytest.mark.parametrize("stream_type", [io.StringIO, io.BytesIO])
def test_scope_error_leaves_caller_stream_open_and_disables_inherited_sink(stream_type):
    primary = io.StringIO()
    log = configure_logger(logger_factory=structlog.PrintLoggerFactory(file=primary))
    with stream_type() as target:
        with pytest.raises(ValueError, match="request failed"):
            with tee_logs(target):
                inherited_context = contextvars.copy_context()
                log.info("before failure")
                raise ValueError("request failed")

        contents = target.getvalue()
        assert not target.closed
        inherited_context.run(log.info, "after failure")
        inherited_context.run(logging.getLogger("late_child").warning, "late stdlib")
        assert target.getvalue() == contents
        assert "after failure" in primary.getvalue()
        assert "late stdlib" in primary.getvalue()


def test_path_target_is_closed_after_scope_exit(tmp_path: Path):
    from structlog_config.tee import _ACTIVE_SINKS

    log = configure_logger()
    with tee_logs(tmp_path / "owned.log"):
        opened_file = _ACTIVE_SINKS.get()[0].file
        log.info("captured")

    assert opened_file.closed


@pytest.mark.parametrize("ending", ["", "\n", "\n\n"])
def test_console_mirror_preserves_trailing_newlines(tmp_path: Path, ending: str):
    primary = io.StringIO()
    log = configure_logger(logger_factory=structlog.PrintLoggerFactory(file=primary))
    target = tmp_path / "newlines.log"

    with tee_logs(target):
        log.info("trailing newline" + ending)

    assert primary.getvalue().endswith(ending + "\n")
    assert target.read_bytes() == primary.getvalue().encode("utf-8")


@pytest.mark.parametrize("terminator", ["", "|", "\n"])
def test_stdlib_mirror_preserves_terminator(tmp_path: Path, terminator: str):
    primary = io.StringIO()
    configure_logger(logger_factory=structlog.PrintLoggerFactory(file=primary))
    handler = logging.getLogger().handlers[0]
    handler.terminator = terminator
    handler.setFormatter(logging.Formatter("%(message)s"))
    target = tmp_path / "terminator.log"

    with tee_logs(target):
        logging.getLogger("terminator").warning("first\n")
        logging.getLogger("terminator").warning("second")

    assert primary.getvalue() == "first\n" + terminator + "second" + terminator
    assert target.read_bytes() == primary.getvalue().encode("utf-8")


@pytest.mark.parametrize("json_logger", [False, True])
@pytest.mark.parametrize("destination", ["stdout", "stderr", "file"])
def test_stdlib_tee_preserves_rendered_records_and_exceptions(
    tmp_path: Path, json_logger: bool, destination: str
):
    target = tmp_path / "mirror.log"
    primary_file = tmp_path / "primary.log"
    log_path = str(primary_file) if destination == "file" else destination

    with temp_env_var({"PYTHON_LOG_PATH": log_path}), CaptureStreams() as capture:
        log = configure_logger(json_logger=json_logger)
        stdlib_log = logging.getLogger("request.library")
        with log.context(request_id="request-123"), tee_logs(target):
            stdlib_log.warning("library diagnostic")
            try:
                raise ValueError("library failure")
            except ValueError:
                stdlib_log.exception("library exception")

    if destination == "file":
        primary_bytes = primary_file.read_bytes()
    elif destination == "stderr":
        primary_bytes = capture.stderr.getvalue().encode("utf-8")
    else:
        primary_bytes = capture.stdout.getvalue().encode("utf-8")

    assert target.read_bytes() == primary_bytes
    assert b"library diagnostic" in primary_bytes
    assert b"library failure" in primary_bytes
    assert b"request-123" in primary_bytes
    if json_logger:
        entries = read_jsonl(target.read_text())
        assert [entry["event"] for entry in entries] == [
            "library diagnostic", "library exception"
        ]
        assert all(entry["request_id"] == "request-123" for entry in entries)
        assert "exception" in entries[1]


def test_existing_and_new_loggers_capture_only_inside_scope(tmp_path: Path):
    """Reuse global logger and bound derivative before, during, and after tee_logs.

    Capture only in-scope events while keeping primary output unchanged.
    Include another module's existing logger and a newly acquired logger.
    """
    log_file = tmp_path / "scope1.log"

    with CaptureStreams() as capture:
        log = configure_logger()
        bound_log = log.bind(component="worker")
        module_log = get_logger("existing_module")
        stdlib_log = logging.getLogger("stdlib_module")

        # 1. Before scope
        log.info("global_before")
        bound_log.info("bound_before")
        module_log.info("module_before")
        stdlib_log.info("stdlib_before")

        # 2. During scope
        with tee_logs(log_file):
            log.info("global_during")
            bound_log.info("bound_during")
            module_log.info("module_during")
            stdlib_log.info("stdlib_during")
            new_log = get_logger("new_module")
            new_log.info("new_during")

        # 3. After scope
        log.info("global_after")
        bound_log.info("bound_after")
        module_log.info("module_after")
        stdlib_log.info("stdlib_after")
        new_log.info("new_after")

    primary_out = capture.stdout.getvalue()
    file_text = log_file.read_text(encoding="utf-8")

    # Mirror contains ONLY in-scope events
    assert "global_during" in file_text
    assert "bound_during" in file_text
    assert "module_during" in file_text
    assert "stdlib_during" in file_text
    assert "new_during" in file_text

    assert "global_before" not in file_text
    assert "bound_before" not in file_text
    assert "module_before" not in file_text
    assert "stdlib_before" not in file_text
    assert "global_after" not in file_text
    assert "bound_after" not in file_text
    assert "module_after" not in file_text
    assert "stdlib_after" not in file_text
    assert "new_after" not in file_text

    # Primary output contains ALL events
    expected_all = [
        "global_before",
        "bound_before",
        "module_before",
        "stdlib_before",
        "global_during",
        "bound_during",
        "module_during",
        "stdlib_during",
        "new_during",
        "global_after",
        "bound_after",
        "module_after",
        "stdlib_after",
        "new_after",
    ]
    for name in expected_all:
        assert name in primary_out


def test_stdlib_warnings_and_file_overrides_respect_capture_and_filters(tmp_path: Path):
    """Include stdlib library logs, warnings routed through this package,

    and non-propagating per-logger path overrides once each.
    Preserve level overrides and dropped-event filtering.
    """
    scope_file = tmp_path / "scope2.log"
    override_file = tmp_path / "custom_override.log"

    def drop_filter(logger, method_name, event_dict):
        if event_dict.get("drop_me"):
            raise DropEvent()
        return event_dict

    with temp_env_var(
        {
            "LOG_PATH_CUSTOM_LIB": str(override_file),
            "LOG_LEVEL_MUTED_LIB": "ERROR",
        }
    ):
        with CaptureStreams() as capture:
            log = configure_logger()
            lib_log = logging.getLogger("custom.lib")
            normal_lib = logging.getLogger("normal.lib")
            muted_lib = logging.getLogger("muted.lib")

            # Attach drop filter to bound logger for dropped-event testing
            bound = log.bind()
            bound._processors = [drop_filter, *bound._processors]

            with tee_logs(scope_file):
                # Stdlib normal logger
                normal_lib.info("normal_lib_msg")

                # Warnings routed through structlog-config
                warnings.simplefilter("always")
                warnings.warn("test_warning_event", UserWarning)

                # Non-propagating per-logger path override
                lib_log.info("override_lib_msg")

                # Level override: muted_lib is ERROR, so INFO is dropped, ERROR is kept
                muted_lib.info("muted_info_dropped")
                muted_lib.error("muted_error_kept")

                # Dropped event via processor DropEvent
                bound.info("kept_event")
                bound.info("dropped_event", drop_me=True)

        scope_text = scope_file.read_text(encoding="utf-8")
        primary_out = capture.stdout.getvalue()
        override_text = override_file.read_text(encoding="utf-8")

        # Normal stdlib log
        assert "normal_lib_msg" in scope_text
        assert "normal_lib_msg" in primary_out

        # Warning
        assert "test_warning_event" in scope_text
        assert "test_warning_event" in primary_out

        # Non-propagating path override: appears once in custom file, once in scope, not in primary stdout
        assert "override_lib_msg" in override_text
        assert "override_lib_msg" in scope_text
        assert "override_lib_msg" not in primary_out
        assert override_text.count("override_lib_msg") == 1
        assert scope_text.count("override_lib_msg") == 1

        # Level overrides
        assert "muted_info_dropped" not in scope_text
        assert "muted_info_dropped" not in primary_out
        assert "muted_error_kept" in scope_text
        assert "muted_error_kept" in primary_out

        # Dropped events
        assert "kept_event" in scope_text
        assert "kept_event" in primary_out
        assert "dropped_event" not in scope_text
        assert "dropped_event" not in primary_out


@pytest.mark.parametrize("json_logger", [False, True])
def test_mirror_preserves_rendering_and_runs_processors_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, json_logger: bool
):
    """Parameterize console/JSON. Compare complete mirrored payloads with compatible primary

    output, including newlines, Unicode, explicitly enabled colors, structured exceptions,
    and context fields. Assert single processor execution, filtering, TRACE, and aliases.
    """
    log_file = tmp_path / "rendering.log"

    # Ensure ANSI colors are enabled in console mode
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr("structlog_config.constants.NO_COLOR", False)
    monkeypatch.setattr("structlog_config.NO_COLOR", False)
    monkeypatch.setattr("structlog_config.formatters.NO_COLOR", False)

    processor_call_count = 0

    def counting_processor(logger, method_name, event_dict):
        nonlocal processor_call_count
        processor_call_count += 1
        return event_dict

    with temp_env_var({"LOG_LEVEL": "TRACE"}), CaptureStreams() as capture:
        log = configure_logger(json_logger=json_logger)
        counting_log = log.bind()
        counting_log._processors = [counting_processor, *counting_log._processors]

        with tee_logs(log_file):
            # Unicode and context aliases
            with log.context(req_id="req-abc"):
                counting_log.info("こんにちは 🚀", greeting="café", emoji="✨")

            counting_log.trace("trace_level_event", trace_key="trace_val")
            counting_log.warn("warn_event")
            counting_log.log(20, "numeric_level_event")

            # Multiline exception
            try:
                raise ValueError("line 1 error\nline 2 detail\nline 3 info")
            except ValueError:
                counting_log.exception("caught_exception")

    file_bytes = log_file.read_bytes()
    file_text = file_bytes.decode("utf-8")
    primary_text = capture.stdout.getvalue()

    assert file_bytes == primary_text.encode("utf-8")

    # Assert single processor execution per event
    assert processor_call_count == 5

    assert "こんにちは 🚀" in file_text
    assert "café" in file_text
    assert "req_id" in file_text
    assert "trace_level_event" in file_text
    assert "warn_event" in file_text
    assert "numeric_level_event" in file_text
    assert "caught_exception" in file_text
    assert "line 1 error" in file_text

    if json_logger:
        entries = read_jsonl(file_text)
        assert len(entries) == 5
        assert entries[0]["event"] == "こんにちは 🚀"
        assert entries[0]["greeting"] == "café"
        assert entries[0]["req_id"] == "req-abc"
        assert entries[1]["event"] == "trace_level_event"
        assert entries[2]["event"] == "warn_event"
        assert entries[3]["event"] == "numeric_level_event"
        assert "exception" in entries[4]
    else:
        # Check ANSI escapes preserved in console mode
        assert "\x1b[" in file_text
        assert "\x1b[" in primary_text


def test_capture_preserves_destinations_and_supports_finalized_configuration(
    tmp_path: Path,
):
    """Cover stdout/stderr, PYTHON_LOG_PATH files, explicit PrintLoggerFactory/BytesLoggerFactory,

    lazy resolution, factory precedence, finalized configuration, and cached loggers.
    """
    # 1. stderr destination via PYTHON_LOG_PATH
    stderr_file = tmp_path / "stderr.log"
    with temp_env_var({"PYTHON_LOG_PATH": "stderr"}), CaptureStreams() as capture:
        log = configure_logger()
        with tee_logs(stderr_file):
            log.info("stderr_event")
        assert "stderr_event" in capture.stderr.getvalue()
        assert capture.stdout.getvalue() == ""
        assert "stderr_event" in stderr_file.read_text(encoding="utf-8")

    # 2. PYTHON_LOG_PATH file destination
    primary_file = tmp_path / "primary_dest.log"
    scope_file = tmp_path / "scope_dest.log"
    with temp_env_var({"PYTHON_LOG_PATH": str(primary_file)}):
        log = configure_logger()
        with tee_logs(scope_file):
            log.info("file_dest_event")
        assert "file_dest_event" in primary_file.read_text(encoding="utf-8")
        assert "file_dest_event" in scope_file.read_text(encoding="utf-8")

    # 3. Factory precedence: explicit factory overrides PYTHON_LOG_PATH
    override_buf = io.StringIO()
    ignored_file = tmp_path / "ignored_file.log"
    prec_file = tmp_path / "prec.log"
    with temp_env_var({"PYTHON_LOG_PATH": str(ignored_file)}):
        log = configure_logger(
            logger_factory=structlog.PrintLoggerFactory(file=override_buf)
        )
        with tee_logs(prec_file):
            log.info("prec_event")
        assert "prec_event" in override_buf.getvalue()
        assert not ignored_file.exists()
        assert "prec_event" in prec_file.read_text(encoding="utf-8")

    # 4. Explicit BytesLoggerFactory
    bytes_buf = io.BytesIO()
    bytes_file = tmp_path / "bytes.log"
    log = configure_logger(
        logger_factory=structlog.BytesLoggerFactory(file=bytes_buf),
        json_logger=True,
    )
    with tee_logs(bytes_file):
        log.info("bytes_event", count=42)
    assert b"bytes_event" in bytes_buf.getvalue()
    bytes_json = read_jsonl(bytes_file.read_text(encoding="utf-8"))
    assert bytes_json[0]["event"] == "bytes_event"
    assert bytes_json[0]["count"] == 42

    # 5. Finalized configuration and cached loggers
    final_file = tmp_path / "final.log"
    log = configure_logger(finalize_configuration=True)
    cached_bound = log.bind(cached=True)
    # Subsequent configure_logger is ignored
    configure_logger(json_logger=True)
    with tee_logs(final_file):
        cached_bound.info("final_cached_event")
    assert "final_cached_event" in final_file.read_text(encoding="utf-8")
    assert "cached=True" in final_file.read_text(encoding="utf-8")


def test_capture_validates_setup_and_preserves_logging_failure_behavior(
    tmp_path: Path,
):
    """Test missing/unsupported configuration rejection before file creation, append mode,

    missing parents, mirror failures, and each stack's existing primary-error behavior.
    Entry/exit must not alter global config, handlers, streams, or levels.
    """
    target = tmp_path / "target.log"

    # 1. Unconfigured structlog rejection before file creation
    structlog.reset_defaults()
    with (
        pytest.raises(
            RuntimeError, match="tee_logs requires structlog.*to be configured"
        ),
        tee_logs(target),
    ):
        pass
    assert not target.exists()

    # 2. Unsupported factory rejection before file creation
    structlog.configure(logger_factory=structlog.WriteLoggerFactory())
    with (
        pytest.raises(
            RuntimeError, match="tee_logs requires structlog.*to be configured"
        ),
        tee_logs(target),
    ):
        pass
    assert not target.exists()

    # 3. Missing parent directory raises FileNotFoundError before touching anything
    log = configure_logger()
    nonexistent = tmp_path / "missing_dir" / "file.log"
    with pytest.raises(FileNotFoundError), tee_logs(nonexistent):
        pass
    assert not (tmp_path / "missing_dir").exists()

    # 4. Append mode: pre-existing content is preserved
    append_file = tmp_path / "append.log"
    append_file.write_bytes(b"prior_content\n")
    with tee_logs(append_file):
        log.info("appended_content")
    appended_text = append_file.read_text(encoding="utf-8")
    assert "prior_content" in appended_text
    assert "appended_content" in appended_text

    # 5. State preservation: entry/exit does not mutate handlers, levels, or streams
    root_logger = logging.getLogger()
    orig_handlers = list(root_logger.handlers)
    orig_level = root_logger.level
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr

    dummy_file = tmp_path / "dummy.log"
    with tee_logs(dummy_file):
        assert list(root_logger.handlers) == orig_handlers
        assert root_logger.level == orig_level
        assert sys.stdout is orig_stdout
        assert sys.stderr is orig_stderr

    assert list(root_logger.handlers) == orig_handlers
    assert root_logger.level == orig_level
    assert sys.stdout is orig_stdout
    assert sys.stderr is orig_stderr

    # 6. Mirror failure propagates after primary success (structlog stack)
    mirror_fail_file = tmp_path / "mirror_fail.log"
    with (
        CaptureStreams() as capture,
        tee_logs(mirror_fail_file),
        mock.patch(
            "structlog_config.tee.emit_to_sinks",
            side_effect=OSError("disk error"),
        ),
        pytest.raises(OSError, match="disk error"),
    ):
        log.info("primary_succeeded_then_mirror_failed")
    assert "primary_succeeded_then_mirror_failed" in capture.stdout.getvalue()

    # 7. Primary failure in stdlib uses handleError and skips mirror
    stdlib_log = logging.getLogger("fail_test")
    scope_file_stdlib = tmp_path / "scope_stdlib_fail.log"
    with tee_logs(scope_file_stdlib):
        handler = root_logger.handlers[0]
        with mock.patch.object(handler, "handleError") as mock_handle_error:
            # Patch handler's stream to fail on write
            with mock.patch.object(
                handler.stream, "write", side_effect=RuntimeError("stream write died")
            ):
                stdlib_log.info("should_trigger_handle_error")
            assert mock_handle_error.called
    assert "should_trigger_handle_error" not in scope_file_stdlib.read_text(
        encoding="utf-8"
    )

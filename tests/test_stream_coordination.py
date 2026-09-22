import io
import logging
import sys
from contextlib import nullcontext
from unittest import mock

import pytest
import structlog

from structlog_config import configure_logger, tee_logs
from tests.capture_utils import CaptureStreams
from tests.utils import read_jsonl, temp_env_var


@pytest.mark.parametrize("enable_tee", [False, True])
def test_stream_coordination_stderr(enable_tee):
    """Test that passing a factory pointing to stderr redirects all logs to stderr."""
    with CaptureStreams() as capture:
        # Configure with a factory pointing to stderr
        logger = configure_logger(
            logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
            enable_tee=enable_tee,
        )

        # Log with structlog
        logger.info("structlog to stderr")

        # Log with stdlib
        stdlib_logger = logging.getLogger("test_stderr_coordination")
        stdlib_logger.info("stdlib to stderr")

    stdout_out = capture.stdout.getvalue()
    stderr_out = capture.stderr.getvalue()

    assert "structlog to stderr" in stderr_out
    assert "stdlib to stderr" in stderr_out
    assert "structlog to stderr" not in stdout_out
    assert "stdlib to stderr" not in stdout_out


@pytest.mark.parametrize("enable_tee", [False, True])
def test_stream_coordination_stdout_explicit(enable_tee):
    """Test that passing a factory pointing to stdout redirects all logs to stdout."""
    with CaptureStreams() as capture:
        # Configure with a factory pointing to stdout
        logger = configure_logger(
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
            enable_tee=enable_tee,
        )

        # Log with structlog
        logger.info("structlog to stdout")

        # Log with stdlib
        stdlib_logger = logging.getLogger("test_stdout_coordination")
        stdlib_logger.info("stdlib to stdout")

    stdout_out = capture.stdout.getvalue()
    stderr_out = capture.stderr.getvalue()

    assert "structlog to stdout" in stdout_out
    assert "stdlib to stdout" in stdout_out
    assert "structlog to stdout" not in stderr_out
    assert "stdlib to stdout" not in stderr_out


@pytest.mark.parametrize("enable_tee", [False, True])
def test_json_stream_coordination_stderr(enable_tee):
    """Test that passing a BytesLoggerFactory pointing to stderr.buffer redirects all logs to stderr."""
    with CaptureStreams() as capture:
        # In JSON mode, we use BytesLoggerFactory which takes a buffer
        logger = configure_logger(
            json_logger=True,
            logger_factory=structlog.BytesLoggerFactory(file=sys.stderr.buffer),
            enable_tee=enable_tee,
        )

        # Log with structlog
        logger.info("structlog json to stderr")

        # Log with stdlib
        stdlib_logger = logging.getLogger("test_json_stderr_coordination")
        stdlib_logger.info("stdlib json to stderr")

    stdout_out = capture.stdout.getvalue()
    stderr_out = capture.stderr.getvalue()

    assert "structlog json to stderr" in stderr_out
    assert "stdlib json to stderr" in stderr_out
    assert "structlog json to stderr" not in stdout_out
    assert "stdlib json to stderr" not in stdout_out


@pytest.mark.parametrize("enable_tee", [False, True])
def test_json_stream_coordination_explicit_factory_overrides_python_log_path(
    tmp_path, enable_tee
):
    """Explicit stream factories should override PYTHON_LOG_PATH coordination."""
    log_file = tmp_path / "ignored.jsonl"

    with temp_env_var({"PYTHON_LOG_PATH": str(log_file)}):
        with CaptureStreams() as capture:
            logger = configure_logger(
                json_logger=True,
                logger_factory=structlog.BytesLoggerFactory(file=sys.stderr.buffer),
                enable_tee=enable_tee,
            )

            logger.info("structlog json to stderr")

            stdlib_logger = logging.getLogger("test_json_stderr_coordination_override")
            stdlib_logger.info("stdlib json to stderr")

        stdout_out = capture.stdout.getvalue()
        stderr_out = capture.stderr.getvalue()

    assert "structlog json to stderr" in stderr_out
    assert "stdlib json to stderr" in stderr_out
    assert "structlog json to stderr" not in stdout_out
    assert "stdlib json to stderr" not in stdout_out
    assert not log_file.exists()


@pytest.mark.parametrize("enable_tee", [False, True])
def test_json_stream_coordination_explicit_factory_overrides_stdout_keyword(enable_tee):
    with temp_env_var({"PYTHON_LOG_PATH": "stdout"}):
        with CaptureStreams() as capture:
            logger = configure_logger(
                json_logger=True,
                logger_factory=structlog.BytesLoggerFactory(file=sys.stderr.buffer),
                enable_tee=enable_tee,
            )

            logger.info("structlog json override stdout keyword")

            stdlib_logger = logging.getLogger("test_json_stdout_keyword_override")
            stdlib_logger.info("stdlib json override stdout keyword")

        stdout_out = capture.stdout.getvalue()
        stderr_out = capture.stderr.getvalue()

    assert "structlog json override stdout keyword" in stderr_out
    assert "stdlib json override stdout keyword" in stderr_out
    assert "structlog json override stdout keyword" not in stdout_out
    assert "stdlib json override stdout keyword" not in stdout_out


@pytest.mark.parametrize("enable_tee", [False, True])
def test_stream_coordination_default(enable_tee):
    """Test that by default logs go to stdout."""
    with CaptureStreams() as capture:
        # Default configuration
        logger = configure_logger(enable_tee=enable_tee)

        # Log with structlog
        logger.info("structlog to default")

        # Log with stdlib
        stdlib_logger = logging.getLogger("test_default_coordination")
        stdlib_logger.info("stdlib to default")

    stdout_out = capture.stdout.getvalue()
    stderr_out = capture.stderr.getvalue()

    assert "structlog to default" in stdout_out
    assert "stdlib to default" in stdout_out
    assert "structlog to default" not in stderr_out
    assert "stdlib to default" not in stderr_out


@pytest.mark.parametrize("enable_tee", [False, True])
def test_bytes_factory_without_json_logger_flag(enable_tee):
    """
    BytesLoggerFactory requires bytes from the processor chain.

    Passing BytesLoggerFactory without json_logger=True previously caused a
    TypeError because the default text processors produce str, and BytesLogger
    does str + b"\\n" when writing.
    """

    with CaptureStreams() as capture:
        logger = configure_logger(
            logger_factory=structlog.BytesLoggerFactory(file=capture.stderr._buffer),
            enable_tee=enable_tee,
        )

        logger.info("bytes factory without json_logger flag")

    assert "bytes factory without json_logger flag" in capture.stderr.getvalue()


@pytest.mark.parametrize("enable_tee", [False, True])
def test_stdlib_logging_with_bytes_stream(enable_tee):
    "Stdlib logging works when logger factory uses a binary stream"

    buffer = io.BytesIO()
    capture = io.BytesIO()
    configure_logger(
        logger_factory=structlog.BytesLoggerFactory(file=buffer),
        json_logger=True,
        enable_tee=enable_tee,
    )
    handler = logging.getLogger().handlers[0]
    stdlib_logger = logging.getLogger("test_binary_stream")
    with (
        tee_logs(capture) if enable_tee else nullcontext(),
        mock.patch.object(
            handler.formatter, "format", wraps=handler.formatter.format
        ) as format_record,
    ):
        stdlib_logger.info("stdlib caf\u00e9 to binary stream")

    assert format_record.call_count == 1
    entries = read_jsonl(buffer.getvalue().decode("utf-8"))
    assert entries[0]["event"] == "stdlib caf\u00e9 to binary stream"
    assert capture.getvalue() == (buffer.getvalue() if enable_tee else b"")
    handler.close()
    assert not buffer.closed


@pytest.mark.parametrize("enable_tee", [False, True])
def test_binary_stream_adapter_encodes_unicode_and_preserves_terminator(enable_tee):
    primary = io.BytesIO()
    target = io.BytesIO()
    configure_logger(
        logger_factory=structlog.BytesLoggerFactory(file=primary),
        json_logger=True,
        enable_tee=enable_tee,
    )
    handler = logging.getLogger().handlers[0]
    # use raw text here because escaped JSON would hide an incorrect ASCII encoder
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.terminator = "|"
    with (
        tee_logs(target) if enable_tee else nullcontext(),
        mock.patch.object(primary, "flush", wraps=primary.flush) as flush,
    ):
        logging.getLogger("unicode_stream").warning("caf\u00e9")
        flush.assert_called_once()

    assert primary.getvalue() == b"caf\xc3\xa9|"
    assert target.getvalue() == (primary.getvalue() if enable_tee else b"")


@pytest.mark.parametrize("enable_tee", [False, True])
@pytest.mark.parametrize("json_logger", [False, True])
@pytest.mark.parametrize("destination", ["stdout", "stderr"])
def test_stdlib_handlers_follow_replaced_standard_streams(
    enable_tee, json_logger, destination
):
    target = io.StringIO()
    with temp_env_var({"PYTHON_LOG_PATH": destination}), CaptureStreams() as initial:
        configure_logger(json_logger=json_logger, enable_tee=enable_tee)
        logger = logging.getLogger("lazy_stream")
        logger.warning("before replacement")

        with (
            CaptureStreams() as replacement,
            tee_logs(target) if enable_tee else nullcontext(),
        ):
            logger.warning("after replacement")

        before = getattr(initial, destination).getvalue()
        after = getattr(replacement, destination).getvalue()
        assert "before replacement" in before
        assert "after replacement" not in before
        assert "after replacement" in after
        assert "before replacement" not in after
        assert target.getvalue() == (after if enable_tee else "")


@pytest.mark.parametrize("enable_tee", [False, True])
@pytest.mark.parametrize("operation", ["write", "flush"])
def test_binary_primary_failures_use_handler_error_policy_and_skip_capture(
    enable_tee, operation
):
    primary = io.BytesIO()
    target = io.BytesIO()
    configure_logger(
        logger_factory=structlog.BytesLoggerFactory(file=primary),
        enable_tee=enable_tee,
        json_logger=True,
    )
    handler = logging.getLogger().handlers[0]
    with (
        tee_logs(target) if enable_tee else nullcontext(),
        mock.patch.object(primary, operation, side_effect=OSError("primary failed")),
        mock.patch.object(handler, "handleError") as handle_error,
    ):
        logging.getLogger("binary_failure").warning("failed output")

    handle_error.assert_called_once()
    assert target.getvalue() == b""


def test_binary_capture_failure_propagates_after_primary_output():
    primary = io.BytesIO()
    target = io.BytesIO()
    configure_logger(
        logger_factory=structlog.BytesLoggerFactory(file=primary),
        enable_tee=True,
        json_logger=True,
    )
    with (
        tee_logs(target),
        mock.patch.object(target, "write", side_effect=OSError("capture failed")),
        pytest.raises(OSError, match="capture failed"),
    ):
        logging.getLogger("capture_failure").warning("primary succeeded")

    assert b"primary succeeded" in primary.getvalue()

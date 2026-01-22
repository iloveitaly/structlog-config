from pathlib import Path, PosixPath

import pytest

from structlog_config import configure_logger


def test_path_prettifier(capsys):
    base_dir = Path.cwd()

    log = configure_logger()
    log.info("message", key=base_dir / "test" / "file.txt")

    log_output = capsys.readouterr()

    assert "Path" not in log_output.out
    assert "path" not in log_output.out


def test_posixpath_prettifier(capsys):
    """
    Original problem was noticing this in the logs:

    2025-05-23 06:41:53 [info     ] direnv environment loaded and cached [test] direnv_state_file=PosixPath('tmp/direnv_state_7f752eb7bf8a5411b7c7d38449299e064b32b9264c15ef6a6943e88106b76f0c')
    """

    base_dir = PosixPath.cwd()

    log = configure_logger()
    log.info("message", key=base_dir / "test" / "file.txt")

    log_output = capsys.readouterr()

    assert "PosixPath" not in log_output.out
    assert "path" not in log_output.out


def test_whenever_formatter_zoned_datetime(capsys):
    """
    Test that whenever.ZonedDateTime objects are formatted without the class wrapper.

    Original problem: seeing ZonedDateTime("2025-11-02 00:00:00+00:00[UTC]") in logs
    Expected: just 2025-11-02T00:00:00+00:00[UTC]
    """
    pytest.importorskip("whenever", reason="whenever package not installed")
    from whenever import ZonedDateTime

    log = configure_logger()
    dt = ZonedDateTime(2025, 11, 2, 0, 0, 0, tz="UTC")
    log.info("message", event_time=dt)

    log_output = capsys.readouterr()

    # Should not contain the class name wrapper
    assert "ZonedDateTime" not in log_output.out
    # Should contain the formatted datetime string
    assert "2025-11-02" in log_output.out
    assert "00:00:00" in log_output.out
    assert "UTC" in log_output.out


def test_whenever_formatter_instant(capsys):
    """
    Test that whenever.Instant objects are formatted cleanly.
    """
    pytest.importorskip("whenever", reason="whenever package not installed")
    from whenever import Instant

    log = configure_logger()
    instant = Instant.from_utc(2025, 11, 2, 12, 30, 45)
    log.info("message", event_instant=instant)

    log_output = capsys.readouterr()

    # Should not contain the class name wrapper
    assert "Instant" not in log_output.out
    # Should contain the formatted instant string
    assert "2025-11-02" in log_output.out


def test_whenever_formatter_local_datetime(capsys):
    """
    Test that whenever.LocalDateTime objects are formatted cleanly.
    """
    pytest.importorskip("whenever", reason="whenever package not installed")
    from whenever import PlainDateTime

    log = configure_logger()
    dt = PlainDateTime(2025, 11, 2, 14, 30)
    log.info("message", local_time=dt)

    log_output = capsys.readouterr()

    # Should not contain the class name wrapper
    assert "PlainDateTime" not in log_output.out
    # Should contain the formatted datetime string
    assert "2025-11-02" in log_output.out
    assert "14:30" in log_output.out

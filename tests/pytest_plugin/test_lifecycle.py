"""Tests for capture across pytest phases."""

from pathlib import Path


def test_setup_failure_creates_setup_file(pytester, plugin_conftest):
    """Setup failure should write output to stdout.txt and exception.txt."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def failing_fixture():
            print("Setup output")
            raise RuntimeError("Setup failed")

        def test_with_failing_fixture(failing_fixture):
            print("This should not run")
            assert True
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1

    test_dir = test_dirs[0]
    assert (test_dir / "stdout.txt").exists()
    assert (test_dir / "exception.txt").exists()

    stdout_content = (test_dir / "stdout.txt").read_text()
    assert "Setup output" in stdout_content

    exception_content = (test_dir / "exception.txt").read_text()
    assert "Setup failed" in exception_content


def test_teardown_failure_creates_teardown_file(pytester, plugin_conftest):
    """Teardown failure should write output to stdout.txt and exception.txt."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def failing_teardown_fixture():
            yield
            print("Teardown output")
            raise RuntimeError("Teardown failed")

        def test_with_failing_teardown(failing_teardown_fixture):
            print("Test runs fine")
            assert True
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1

    test_dir = test_dirs[0]
    assert (test_dir / "stdout.txt").exists()
    assert (test_dir / "exception.txt").exists()

    stdout_content = (test_dir / "stdout.txt").read_text()
    assert "Test runs fine" in stdout_content
    assert "Teardown output" in stdout_content

    exception_content = (test_dir / "exception.txt").read_text()
    assert "Teardown failed" in exception_content


def test_captures_logs_from_makereport_phase(pytester, plugin_conftest):
    """Logs emitted during pytest_runtest_makereport should be captured."""
    pytester.makeconftest(
        plugin_conftest
        + """
import pytest
import structlog

log = structlog.get_logger(logger_name="test_makereport_plugin")

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        log.info("makereport phase log message")
    """
    )

    pytester.makepyfile(
        """
def test_failing():
    print("test output")
    assert False, "Test failed"
    """
    )

    result = pytester.runpytest(
        "--structlog-output=test-output", "-s", "-p", "no:logging"
    )
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1

    test_dir = test_dirs[0]
    assert (test_dir / "stdout.txt").exists()

    stdout_content = (test_dir / "stdout.txt").read_text()
    assert "makereport phase log message" not in stdout_content
    assert "test output" in stdout_content


def test_captures_newly_created_loggers(pytester, plugin_conftest):
    """Loggers created during test execution should be captured."""
    pytester.makeconftest(
        plugin_conftest
        + """
from structlog_config import configure_logger

configure_logger()
    """
    )
    pytester.makepyfile(
        """
        import logging
        import structlog

        def test_new_loggers():
            # Create new structlog logger during test
            new_structlog = structlog.get_logger("new_module")
            new_structlog.info("structlog message from new logger")

            # Create new stdlib logger during test
            new_stdlib = logging.getLogger("another_new_module")
            new_stdlib.warning("stdlib warning from new logger")

            print("Regular print statement")

            assert False, "Test failed"
        """
    )

    result = pytester.runpytest(
        "--structlog-output=test-output", "-s", "-p", "no:logging"
    )
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1

    test_dir = test_dirs[0]
    assert (test_dir / "stdout.txt").exists()

    stdout_content = (test_dir / "stdout.txt").read_text()

    # All output should be captured
    assert "structlog message from new logger" in stdout_content
    assert "stdlib warning from new logger" in stdout_content
    assert "Regular print statement" in stdout_content

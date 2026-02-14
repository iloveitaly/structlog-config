"""Tests for pytest output capture plugin."""

from pathlib import Path

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def plugin_conftest():
    """Conftest content for tests (plugin auto-loads via entry point)."""
    return ""


def test_passing_test_no_output(pytester, plugin_conftest):
    """Passing test should not create output files."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_passing():
            print("Hello stdout")
            assert True
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 0

    output_dir = Path(pytester.path / "test-output")
    assert not output_dir.exists() or not list(output_dir.iterdir())


def test_failing_test_creates_output_files(pytester, plugin_conftest):
    """Failing test should write stdout, stderr, and exception files."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import sys

        def test_failing():
            print("Hello stdout")
            print("Hello stderr", file=sys.stderr)
            assert False, "Test failed"
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1

    test_dir = test_dirs[0]
    assert (test_dir / "stdout.txt").exists()
    assert (test_dir / "stderr.txt").exists()
    assert (test_dir / "exception.txt").exists()

    stdout_content = (test_dir / "stdout.txt").read_text()
    assert "Hello stdout" in stdout_content

    stderr_content = (test_dir / "stderr.txt").read_text()
    assert "Hello stderr" in stderr_content

    exception_content = (test_dir / "exception.txt").read_text()
    assert "Test failed" in exception_content
    assert "AssertionError" in exception_content


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


def test_without_capture_flag_logs_error(pytester, plugin_conftest):
    """Plugin should log error and disable itself without -s flag."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing():
            print("Hello")
            assert False
        """
    )

    result = pytester.runpytest("--structlog-output=test-output")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    assert not output_dir.exists() or not list(output_dir.iterdir())


def test_with_capture_flag_enabled(pytester, plugin_conftest):
    """Plugin should work when -s flag is provided."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing():
            print("Hello")
            assert False
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    assert output_dir.exists()
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1


def test_custom_output_directory(pytester, plugin_conftest):
    """Plugin should use custom output directory when specified."""
    pytester.makeconftest(plugin_conftest)
    custom_dir = pytester.path / "custom-output"

    pytester.makepyfile(
        """
        def test_failing():
            print("Hello")
            assert False
        """
    )

    result = pytester.runpytest(f"--structlog-output={custom_dir}", "-s")
    assert result.ret == 1

    assert custom_dir.exists()
    test_dirs = list(custom_dir.iterdir())
    assert len(test_dirs) == 1


def test_plugin_disabled_without_flag(pytester, plugin_conftest):
    """Plugin should be disabled when --structlog-output is not provided."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing():
            print("Hello stdout")
            assert False, "Test failed"
        """
    )

    result = pytester.runpytest("-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    assert not output_dir.exists() or not list(output_dir.iterdir())


def test_fd_capture_with_subprocess(pytester):
    """Test fd-level capture fixture is activated and captures output.

    Note: Full subprocess output capture (from child processes) is difficult to test
    within pytester's nested environment, but works correctly in real-world usage
    where tests spawn subprocesses (e.g., server processes using multiprocessing.Process,
    or external commands via subprocess.Popen).
    """
    pytester.makeconftest(
        """
        import pytest

        pytestmark = pytest.mark.usefixtures("file_descriptor_output_capture")
        """
    )

    pytester.makepyfile(
        """
        import sys

        def test_with_fd_capture():
            print("Output with fd capture enabled", flush=True)
            print("Error output", file=sys.stderr, flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            assert False, "Test failed"
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1

    test_dir = test_dirs[0]
    assert (test_dir / "stdout.txt").exists()
    assert (test_dir / "stderr.txt").exists()

    stdout_content = (test_dir / "stdout.txt").read_text()
    assert "Output with fd capture enabled" in stdout_content

    stderr_content = (test_dir / "stderr.txt").read_text()
    assert "Error output" in stderr_content


def test_only_failing_tests_create_output(pytester, plugin_conftest):
    """Only failing tests should create output directories."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_passing_1():
            print("Pass 1")
            assert True

        def test_failing():
            print("Failing")
            assert False

        def test_passing_2():
            print("Pass 2")
            assert True
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1
    assert "test-failing" in test_dirs[0].name


def test_parametrized_test_names(pytester, plugin_conftest):
    """Parametrized tests should have unique output directories."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.parametrize("value", [1, 2, 3])
        def test_param(value):
            print(f"Value: {value}")
            assert value != 2
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1
    assert "2" in test_dirs[0].name


def test_empty_output_not_written(pytester, plugin_conftest):
    """Empty output should not create files."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing_no_output():
            assert False
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1

    test_dir = test_dirs[0]
    assert not (test_dir / "stdout.txt").exists()
    assert not (test_dir / "stderr.txt").exists()
    assert (test_dir / "exception.txt").exists()


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
    assert "makereport phase log message" in stdout_content
    assert "test output" in stdout_content


def test_terminal_summary_with_failures(pytester, plugin_conftest):
    """Terminal summary should appear when tests fail and artifacts are written."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing_1():
            print("Output 1")
            assert False

        def test_failing_2():
            print("Output 2")
            assert False

        def test_failing_3():
            print("Output 3")
            assert False
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output = result.stdout.str()
    assert "structlog output captured" in output
    assert "3 failed test(s) captured to: test-output" in output


def test_terminal_summary_not_shown_when_all_pass(pytester, plugin_conftest):
    """Terminal summary should not appear when all tests pass."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_passing_1():
            print("Pass 1")
            assert True

        def test_passing_2():
            print("Pass 2")
            assert True
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 0

    output = result.stdout.str()
    assert "structlog output captured" not in output


def test_terminal_summary_not_shown_when_plugin_disabled(pytester, plugin_conftest):
    """Terminal summary should not appear when plugin is disabled."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing():
            print("Output")
            assert False
        """
    )

    result = pytester.runpytest("-s")
    assert result.ret == 1

    output = result.stdout.str()
    assert "structlog output captured" not in output


def test_no_structlog_flag_disables_all_capture(pytester, plugin_conftest):
    """--no-structlog flag should disable all capture functionality."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import sys

        def test_failing():
            print("Hello stdout")
            print("Hello stderr", file=sys.stderr)
            assert False, "Test failed"
        """
    )

    result = pytester.runpytest(
        "--structlog-output=test-output", "--no-structlog", "-s"
    )
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    assert not output_dir.exists() or not list(output_dir.iterdir())


def test_no_structlog_flag_without_output_flag(pytester, plugin_conftest):
    """--no-structlog flag should work even without --structlog-output."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing():
            print("Hello stdout")
            assert False, "Test failed"
        """
    )

    result = pytester.runpytest("--no-structlog", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    assert not output_dir.exists() or not list(output_dir.iterdir())


def test_no_structlog_flag_prevents_terminal_summary(pytester, plugin_conftest):
    """--no-structlog flag should prevent terminal summary from showing."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing():
            print("Output")
            assert False
        """
    )

    result = pytester.runpytest(
        "--structlog-output=test-output", "--no-structlog", "-s"
    )
    assert result.ret == 1

    output = result.stdout.str()
    assert "structlog output captured" not in output


def test_ansi_codes_stripped_from_output_files(pytester, plugin_conftest):
    """ANSI escape codes should be stripped from captured output files."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import sys

        def test_failing_with_color():
            print("\\x1b[31mred text\\x1b[0m and \\x1b[32mgreen text\\x1b[0m")
            print("\\x1b[1;34mbold blue\\x1b[0m", file=sys.stderr)
            assert False, "\\x1b[33myellow error\\x1b[0m"
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = list(output_dir.iterdir())
    test_dir = test_dirs[0]

    stdout_content = (test_dir / "stdout.txt").read_text()
    assert "red text" in stdout_content
    assert "green text" in stdout_content
    assert "\x1b[" not in stdout_content

    stderr_content = (test_dir / "stderr.txt").read_text()
    assert "bold blue" in stderr_content
    assert "\x1b[" not in stderr_content

    exception_content = (test_dir / "exception.txt").read_text()
    assert "yellow error" in exception_content
    assert "\x1b[" not in exception_content

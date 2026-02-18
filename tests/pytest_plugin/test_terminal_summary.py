"""Tests for terminal output."""

import json
import re


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
    assert "[failed]" in output
    assert "test_failing_1" in output
    assert "test_failing_2" in output
    assert "test_failing_3" in output
    assert "logs: test-output/" in output
    assert "AssertionError" in output


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


def test_failure_traceback_visible_in_terminal(pytester, plugin_conftest):
    """Failure traceback should appear in terminal output when --structlog-output is enabled."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing():
            assert False, "the specific error message"
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output = result.stdout.str()
    assert "FAILED" in output
    assert "AssertionError" in output
    assert "the specific error message" in output


def test_failure_traceback_visible_with_setup_failure(pytester, plugin_conftest):
    """Setup failure traceback should appear in terminal output."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def failing_setup():
            raise RuntimeError("the specific setup error message")

        def test_with_failing_setup(failing_setup):
            pass
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output = result.stdout.str()
    assert "RuntimeError" in output
    assert "the specific setup error message" in output


def test_failure_traceback_visible_with_teardown_failure(pytester, plugin_conftest):
    """Teardown failure traceback should appear in terminal output."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def failing_teardown():
            yield
            raise RuntimeError("the specific teardown error message")

        def test_with_failing_teardown(failing_teardown):
            pass
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output = result.stdout.str()
    assert "RuntimeError" in output
    assert "the specific teardown error message" in output


def test_failed_test_shows_duration(pytester, plugin_conftest):
    """Failed test entry in summary should include a duration."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing():
            assert False
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output = result.stdout.str()
    assert re.search(r"\[failed\] \d+\.\d+s", output)


def test_slow_passing_test_shows_slow_tag(pytester, plugin_conftest):
    """A passing test exceeding the slow threshold should appear in the slow section."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import time

        def test_slow():
            time.sleep(0.2)
        """
    )

    result = pytester.runpytest(
        "--structlog-output=test-output", "-s", "--slow-test-threshold=0.1"
    )
    assert result.ret == 0

    output = result.stdout.str()
    assert "[slow]" in output
    assert "test_slow" in output


def test_fast_passing_test_not_shown(pytester, plugin_conftest):
    """A passing test under the slow threshold should not appear in the slow section."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_fast():
            pass
        """
    )

    result = pytester.runpytest("--slow-test-threshold=1.0")
    assert result.ret == 0

    output = result.stdout.str()
    assert "[slow]" not in output


def test_slow_threshold_zero_disables_slow_reporting(pytester, plugin_conftest):
    """Setting --slow-test-threshold=0 should disable the slow tests section entirely."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import time

        def test_slow():
            time.sleep(0.2)
        """
    )

    result = pytester.runpytest("--slow-test-threshold=0")
    assert result.ret == 0

    output = result.stdout.str()
    assert "[slow]" not in output


def test_slow_tests_sorted_by_duration(pytester, plugin_conftest):
    """Slow tests should appear sorted from slowest to fastest."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import time

        def test_slower():
            time.sleep(0.3)

        def test_faster():
            time.sleep(0.1)
        """
    )

    result = pytester.runpytest("--slow-test-threshold=0.05")
    assert result.ret == 0

    output = result.stdout.str()
    assert "[slow]" in output
    slower_pos = output.index("test_slower")
    faster_pos = output.index("test_faster")
    assert slower_pos < faster_pos


def test_no_color_suppresses_ansi_in_slow_output(
    pytester, plugin_conftest, monkeypatch
):
    """NO_COLOR env var should suppress ANSI codes in the slow tests section."""
    monkeypatch.setenv("NO_COLOR", "1")
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import time

        def test_slow():
            time.sleep(0.2)
        """
    )

    result = pytester.runpytest("--slow-test-threshold=0.1")
    output = result.stdout.str()

    slow_line = next((line for line in output.splitlines() if "[slow]" in line), None)
    assert slow_line is not None
    assert "\x1b[" not in slow_line


def test_slow_tests_shown_without_structlog_output(pytester, plugin_conftest):
    """Slow test reporting is active even without --structlog-output."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import time

        def test_slow():
            time.sleep(0.2)
        """
    )

    result = pytester.runpytest("--slow-test-threshold=0.1")
    assert result.ret == 0

    output = result.stdout.str()
    assert "[slow]" in output
    assert "test_slow" in output


def test_results_json_written_on_failure(pytester, plugin_conftest):
    """results.json should be written to the output dir when tests fail."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing_1():
            assert False, "first failure"

        def test_failing_2():
            assert False, "second failure"
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    results_path = pytester.path / "test-output" / "results.json"
    assert results_path.exists()

    data = json.loads(results_path.read_text())
    assert isinstance(data, list)
    assert len(data) == 2

    for failure in data:
        assert "file" in failure
        assert "test" in failure
        assert isinstance(failure["line"], int)
        assert "exception" in failure
        assert "logs" in failure

        logs_dir = pytester.path / "test-output" / failure["logs"]
        assert logs_dir.exists()


def test_no_structlog_flag_disables_timing(pytester, plugin_conftest):
    """--no-structlog should disable the slow tests section."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import time

        def test_slow():
            time.sleep(0.2)
        """
    )

    result = pytester.runpytest("--no-structlog", "--slow-test-threshold=0.1")
    assert result.ret == 0

    output = result.stdout.str()
    assert "[slow]" not in output

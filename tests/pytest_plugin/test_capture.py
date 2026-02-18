"""Tests for core capture behavior - what gets written to disk."""

import json
from pathlib import Path


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


def test_skipped_test_no_output(pytester, plugin_conftest):
    """Skipped test should not create output files."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import pytest

        def test_skipped():
            print("Hello from skipped test")
            pytest.skip("Skipping this test")
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
    test_dirs = [p for p in output_dir.iterdir() if p.is_dir()]
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
    test_dirs = [p for p in output_dir.iterdir() if p.is_dir()]
    assert len(test_dirs) == 1
    assert "test-failing" in test_dirs[0].name


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
    test_dirs = [p for p in output_dir.iterdir() if p.is_dir()]
    assert len(test_dirs) == 1

    test_dir = test_dirs[0]
    assert not (test_dir / "stdout.txt").exists()
    assert not (test_dir / "stderr.txt").exists()
    assert (test_dir / "exception.txt").exists()


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
    test_dirs = [p for p in output_dir.iterdir() if p.is_dir()]
    assert len(test_dirs) == 1
    assert "2" in test_dirs[0].name


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
    test_dirs = [p for p in output_dir.iterdir() if p.is_dir()]
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


def test_failing_test_creates_exception_json(pytester, plugin_conftest):
    """Failing test should produce exception.json alongside exception.txt."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_failing():
            assert False, "boom goes the dynamite"
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = [p for p in output_dir.iterdir() if p.is_dir()]
    test_dir = test_dirs[0]

    assert (test_dir / "exception.json").exists()

    exc_data = json.loads((test_dir / "exception.json").read_text())
    assert "exception" in exc_data
    assert "message" in exc_data
    assert exc_data["exception"] == "AssertionError"
    assert "boom goes the dynamite" in exc_data["message"]


def test_exception_json_includes_chained_exceptions(pytester, plugin_conftest):
    """raise X from Y should produce a 'chain' key in exception.json."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        def test_chained():
            try:
                raise ValueError("original error")
            except ValueError as e:
                raise RuntimeError("wrapped error") from e
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output_dir = Path(pytester.path / "test-output")
    test_dirs = [p for p in output_dir.iterdir() if p.is_dir()]
    test_dir = test_dirs[0]

    assert (test_dir / "exception.json").exists()

    exc_data = json.loads((test_dir / "exception.json").read_text())
    assert "chain" in exc_data
    chain_exceptions = [entry["exception"] for entry in exc_data["chain"]]
    assert "ValueError" in chain_exceptions


def test_persist_failed_only_false_keeps_passing_tests(pytester, monkeypatch):
    """When PERSIST_FAILED_ONLY=False, passing test output should be persisted."""
    import structlog_config.pytest_plugin

    monkeypatch.setattr(structlog_config.pytest_plugin, "PERSIST_FAILED_ONLY", False)

    pytester.makeconftest("")
    pytester.makepyfile(
        """
        def test_passing():
            print("Hello from passing test")
            assert True
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 0

    output_dir = Path(pytester.path / "test-output")
    test_dirs = [p for p in output_dir.iterdir() if p.is_dir()]
    assert len(test_dirs) == 1

    test_dir = test_dirs[0]
    assert (test_dir / "stdout.txt").exists()

    stdout_content = (test_dir / "stdout.txt").read_text()
    assert "Hello from passing test" in stdout_content

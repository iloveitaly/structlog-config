"""Tests for CLI flags and plugin activation."""

from pathlib import Path


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


def test_fd_capture_fixture_respects_no_structlog_flag(pytester, plugin_conftest):
    """file_descriptor_output_capture fixture should skip when --no-structlog is used."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.usefixtures("file_descriptor_output_capture")
        def test_with_fd_capture():
            print("stdout from test")
            assert True
        """
    )

    result = pytester.runpytest("--no-structlog", "-s")
    assert result.ret == 0

    output = result.stdout.str()
    assert "skipping fd capture, structlog output capture is disabled" in output
    assert "starting output capture" not in output


def test_fd_capture_fixture_works_when_enabled(pytester, plugin_conftest):
    """file_descriptor_output_capture fixture should activate when structlog is enabled."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.usefixtures("file_descriptor_output_capture")
        def test_failing_with_fd_capture():
            import sys
            print("stdout from test", flush=True)
            print("stderr from test", file=sys.stderr, flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            assert False
        """
    )

    result = pytester.runpytest("--structlog-output=test-output", "-s")
    assert result.ret == 1

    output = result.stdout.str()
    assert "skipping fd capture" not in output

    output_dir = Path(pytester.path / "test-output")
    assert output_dir.exists()
    test_dirs = list(output_dir.iterdir())
    assert len(test_dirs) == 1

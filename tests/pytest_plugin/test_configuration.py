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

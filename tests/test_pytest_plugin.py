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
    """Setup failure should write setup.txt."""
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
    assert (test_dir / "setup.txt").exists()

    setup_content = (test_dir / "setup.txt").read_text()
    assert "Setup output" in setup_content
    assert "Setup failed" in setup_content


def test_teardown_failure_creates_teardown_file(pytester, plugin_conftest):
    """Teardown failure should write teardown.txt."""
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
    assert (test_dir / "teardown.txt").exists()

    teardown_content = (test_dir / "teardown.txt").read_text()
    assert "Teardown output" in teardown_content
    assert "Teardown failed" in teardown_content


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
    """Test fd-level capture using conftest fixture."""
    pytester.makeconftest(
        """
        import pytest

        pytestmark = pytest.mark.usefixtures("file_descriptor_output_capture")
        """
    )

    pytester.makepyfile(
        """
        import sys

        def test_subprocess():
            print("Hello from print", flush=True)
            sys.stdout.flush()
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

    stdout_content = (test_dir / "stdout.txt").read_text()
    assert "Hello from print" in stdout_content


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
    assert "test_failing" in test_dirs[0].name


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

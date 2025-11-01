"""Tests for the pytest plugin that captures logs on test failures."""

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def plugin_conftest():
    """Conftest content that registers the plugin."""
    return """
pytest_plugins = ["structlog_config.pytest_plugin"]
"""


def test_plugin_registers_option(pytester: pytest.Pytester, plugin_conftest):
    """Test that --capture-logs-on-fail option is registered."""
    pytester.makeconftest(plugin_conftest)
    result = pytester.runpytest("--help")
    result.stdout.fnmatch_lines(["*--capture-logs-on-fail*"])
    result.stdout.fnmatch_lines(["*--capture-logs-dir*"])


def test_plugin_disabled_by_default(pytester: pytest.Pytester, plugin_conftest):
    """Test that plugin is disabled when flag is not set."""
    pytester.makeconftest(plugin_conftest)
    pytester.makepyfile(
        """
        import structlog
        log = structlog.get_logger()
        
        def test_failing():
            log.error("This should not appear")
            assert False
        """
    )
    
    result = pytester.runpytest("-v")
    assert result.ret == 1
    assert "Captured logs for failed test" not in result.stdout.str()


def test_plugin_sets_env_var_per_test(pytester: pytest.Pytester):
    """Test that PYTHON_LOG_PATH is set for each test."""
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        """
    )
    pytester.makepyfile(
        """
        import os
        
        def test_env_var_is_set():
            assert "PYTHON_LOG_PATH" in os.environ
            assert os.environ["PYTHON_LOG_PATH"].endswith(".log")
        """
    )
    
    result = pytester.runpytest("--capture-logs-on-fail", "-v")
    assert result.ret == 0


def test_plugin_no_logs_for_passing_tests(pytester: pytest.Pytester):
    """Test that logs are not displayed for passing tests."""
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        
        import structlog
        from structlog_config import configure_logger
        
        def pytest_configure(config):
            configure_logger()
        """
    )
    pytester.makepyfile(
        """
        import structlog
        log = structlog.get_logger()
        
        def test_passing():
            log.info("This should not be displayed")
            assert True
        """
    )
    
    result = pytester.runpytest("--capture-logs-on-fail", "-v")
    assert result.ret == 0
    assert "Captured logs" not in result.stdout.str()


def test_plugin_creates_unique_log_files(pytester: pytest.Pytester, tmp_path):
    """Test that each test gets a unique log file."""
    logs_dir = tmp_path / "test-logs"
    
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        """
    )
    pytester.makepyfile(
        """
        import os
        
        log_paths = []
        
        def test_one():
            log_paths.append(os.environ["PYTHON_LOG_PATH"])
            
        def test_two():
            log_paths.append(os.environ["PYTHON_LOG_PATH"])
            assert log_paths[0] != log_paths[1]
        """
    )
    
    result = pytester.runpytest(f"--capture-logs-dir={logs_dir}", "-v")
    assert result.ret == 0


def test_plugin_creates_session_tmpdir(pytester: pytest.Pytester):
    """Test that plugin creates and cleans up session temp directory."""
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        
        import os
        from pathlib import Path
        
        session_tmpdir = None
        
        def pytest_sessionstart(session):
            global session_tmpdir
            plugin_config = session.config.stash.get(__import__("structlog_config.pytest_plugin", fromlist=["PLUGIN_KEY"]).PLUGIN_KEY, {})
            session_tmpdir = plugin_config.get("session_tmpdir")
        """
    )
    pytester.makepyfile(
        """
        def test_something():
            assert True
        """
    )
    
    result = pytester.runpytest("--capture-logs-on-fail", "-v")
    assert result.ret == 0


def test_plugin_handles_empty_log_files(pytester: pytest.Pytester):
    """Test that plugin handles tests with no log output gracefully."""
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        
        from structlog_config import configure_logger
        
        def pytest_configure(config):
            configure_logger()
        """
    )
    pytester.makepyfile(
        """
        def test_failing_no_logs():
            assert False
        """
    )
    
    result = pytester.runpytest("--capture-logs-on-fail", "-v")
    assert result.ret == 1
    assert "Captured logs for failed test" not in result.stdout.str()


def test_plugin_with_capture_logs_dir(pytester: pytest.Pytester, tmp_path):
    """Test that --capture-logs-dir creates the directory."""
    logs_dir = tmp_path / "test-logs"
    
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        """
    )
    pytester.makepyfile(
        """
        def test_one():
            assert True
        """
    )
    
    result = pytester.runpytest(f"--capture-logs-dir={logs_dir}", "-v")
    assert result.ret == 0
    assert logs_dir.exists()


def test_plugin_sanitizes_test_names(pytester: pytest.Pytester):
    """Test that test names with special characters are sanitized for filenames."""
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        """
    )
    pytester.makepyfile(
        """
        import os
        import pytest
        
        @pytest.mark.parametrize("value", [1, 2])
        def test_with_params(value):
            log_path = os.environ["PYTHON_LOG_PATH"]
            assert "[" not in log_path
            assert "]" not in log_path
            assert value in [1, 2]
        """
    )
    
    result = pytester.runpytest("--capture-logs-on-fail", "-v")
    assert result.ret == 0


def test_plugin_disabled_when_python_log_path_set(pytester: pytest.Pytester):
    """Test that plugin is disabled when PYTHON_LOG_PATH is already set."""
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        
        import os
        import structlog
        from structlog_config import configure_logger
        
        def pytest_configure(config):
            os.environ["PYTHON_LOG_PATH"] = "/tmp/existing.log"
            configure_logger()
        """
    )
    pytester.makepyfile(
        """
        def test_failing():
            assert False
        """
    )
    
    result = pytester.runpytest("--capture-logs-on-fail", "-v")
    assert result.ret == 1
    result.stdout.fnmatch_lines([
        "*PYTHON_LOG_PATH is already set*disabled*",
    ])


def test_plugin_multiple_test_files(pytester: pytest.Pytester):
    """Test that plugin works correctly with multiple test files."""
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        """
    )
    pytester.makepyfile(
        test_file_1="""
        import os
        
        def test_file_1():
            assert "PYTHON_LOG_PATH" in os.environ
        """,
        test_file_2="""
        import os
        
        def test_file_2():
            assert "PYTHON_LOG_PATH" in os.environ
        """
    )
    
    result = pytester.runpytest("--capture-logs-on-fail", "-v")
    assert result.ret == 0


def test_plugin_capture_logs_dir_enables_plugin(pytester: pytest.Pytester, tmp_path):
    """Test that --capture-logs-dir alone enables the plugin without --capture-logs-on-fail."""
    logs_dir = tmp_path / "test-logs"
    
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        """
    )
    pytester.makepyfile(
        """
        import os
        
        def test_one():
            assert "PYTHON_LOG_PATH" in os.environ
        """
    )
    
    result = pytester.runpytest(f"--capture-logs-dir={logs_dir}", "-v")
    assert result.ret == 0
    assert logs_dir.exists()


def test_plugin_restores_original_python_log_path(pytester: pytest.Pytester):
    """Test that plugin restores original PYTHON_LOG_PATH after test."""
    pytester.makeconftest(
        """
        pytest_plugins = ["structlog_config.pytest_plugin"]
        
        import os
        from structlog_config import configure_logger
        
        def pytest_configure(config):
            configure_logger()
        """
    )
    pytester.makepyfile(
        """
        import os
        
        def test_env_restored():
            original = os.environ.get("PYTHON_LOG_PATH")
            assert original is not None
        """
    )
    
    result = pytester.runpytest("--capture-logs-on-fail", "-v")
    assert result.ret == 0


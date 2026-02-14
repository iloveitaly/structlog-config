"""Tests for terminal output."""


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

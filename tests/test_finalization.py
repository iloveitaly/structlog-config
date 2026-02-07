import structlog_config
from structlog_config import configure_logger


def test_finalize_configuration(stdout_capture):
    # Reset the module-level state for testing
    structlog_config._CONFIGURATION_FINALIZED = False

    # First call, finalize it
    configure_logger(finalize_configuration=True)
    assert structlog_config._CONFIGURATION_FINALIZED is True

    # Second call, should log a warning and return a logger
    with stdout_capture as capture:
        configure_logger(json_logger=True)

    output = capture.getvalue()
    assert "configure_logger called after finalized configuration, ignoring" in output

    # Clean up
    structlog_config._CONFIGURATION_FINALIZED = False


def test_not_finalized_by_default():
    structlog_config._CONFIGURATION_FINALIZED = False

    configure_logger(finalize_configuration=False)
    assert structlog_config._CONFIGURATION_FINALIZED is False

    configure_logger(finalize_configuration=False)
    assert structlog_config._CONFIGURATION_FINALIZED is False

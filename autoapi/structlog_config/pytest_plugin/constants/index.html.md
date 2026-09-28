# structlog_config.pytest_plugin.constants

## Attributes

| [`logger`](#structlog_config.pytest_plugin.constants.logger)                   |                                                                                           |
|---------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| [`CAPTURE_KEY`](#structlog_config.pytest_plugin.constants.CAPTURE_KEY)              | Stash key for the plugin's config dict on pytest.Config.                                  |
| [`CAPTURED_TESTS_KEY`](#structlog_config.pytest_plugin.constants.CAPTURED_TESTS_KEY)       | Stash key for the list of failed tests that had output captured.                          |
| [`SLOW_THRESHOLD_KEY`](#structlog_config.pytest_plugin.constants.SLOW_THRESHOLD_KEY)       | Stash key for the slow test threshold in seconds; None means slow reporting is disabled.  |
| [`SLOW_TESTS_DISPLAY_LIMIT`](#structlog_config.pytest_plugin.constants.SLOW_TESTS_DISPLAY_LIMIT) | Max number of slow tests listed in the terminal summary before truncating.                |
| [`PLUGIN_NAMESPACE`](#structlog_config.pytest_plugin.constants.PLUGIN_NAMESPACE)         | Namespace used when registering options and artifact dirs with pytest-plugin-utils.       |
| [`SUBPROCESS_CAPTURE_ENV`](#structlog_config.pytest_plugin.constants.SUBPROCESS_CAPTURE_ENV)   | Env var set per-test so spawned subprocesses know which artifact directory to write into. |
| [`CAPTURE_ENABLED_KEY`](#structlog_config.pytest_plugin.constants.CAPTURE_ENABLED_KEY)      | Key in the CAPTURE_KEY stash dict that indicates whether the plugin is active.            |
| [`CAPTURE_OUTPUT_DIR_KEY`](#structlog_config.pytest_plugin.constants.CAPTURE_OUTPUT_DIR_KEY)   | Key in the CAPTURE_KEY stash dict that holds the root output directory path.              |
| [`CAPTURE_PERSIST_ALL_KEY`](#structlog_config.pytest_plugin.constants.CAPTURE_PERSIST_ALL_KEY)  | Key in the CAPTURE_KEY stash dict that controls whether passing test artifacts are kept.  |

## Classes

| [`CapturedTestFailure`](#structlog_config.pytest_plugin.constants.CapturedTestFailure)   |    |
|------------------------------------------------------------------------|----|

## Module Contents

### structlog_config.pytest_plugin.constants.logger

### *class* structlog_config.pytest_plugin.constants.CapturedTestFailure

#### nodeid *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### file *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### line *: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None)*

#### artifact_dir *: [pathlib.Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### exception_summary *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

#### duration *: [float](https://docs.python.org/3/builtins/functions.html#float) | [None](https://docs.python.org/3/builtins/constants.html#None)* *= None*

### structlog_config.pytest_plugin.constants.CAPTURE_KEY

Stash key for the plugin’s config dict on pytest.Config.

### structlog_config.pytest_plugin.constants.CAPTURED_TESTS_KEY

Stash key for the list of failed tests that had output captured.

### structlog_config.pytest_plugin.constants.SLOW_THRESHOLD_KEY

Stash key for the slow test threshold in seconds; None means slow reporting is disabled.

### structlog_config.pytest_plugin.constants.SLOW_TESTS_DISPLAY_LIMIT *= 10*

Max number of slow tests listed in the terminal summary before truncating.

### structlog_config.pytest_plugin.constants.PLUGIN_NAMESPACE *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'structlog_config'*

Namespace used when registering options and artifact dirs with pytest-plugin-utils.

### structlog_config.pytest_plugin.constants.SUBPROCESS_CAPTURE_ENV *= 'STRUCTLOG_CAPTURE_DIR'*

Env var set per-test so spawned subprocesses know which artifact directory to write into.

### structlog_config.pytest_plugin.constants.CAPTURE_ENABLED_KEY *= 'enabled'*

Key in the CAPTURE_KEY stash dict that indicates whether the plugin is active.

### structlog_config.pytest_plugin.constants.CAPTURE_OUTPUT_DIR_KEY *= 'output_dir'*

Key in the CAPTURE_KEY stash dict that holds the root output directory path.

### structlog_config.pytest_plugin.constants.CAPTURE_PERSIST_ALL_KEY *= 'persist_all'*

Key in the CAPTURE_KEY stash dict that controls whether passing test artifacts are kept.

import os
from contextlib import contextmanager
from typing import Dict


@contextmanager
def temp_env_var(env_vars: Dict[str, str]):
    """
    Context manager for temporarily setting environment variables.

    Args:
        env_vars: Dictionary of environment variables to set

    Example:
        with temp_env_var({"LOG_LEVEL": "DEBUG"}):
            # Code that depends on LOG_LEVEL being DEBUG
            ...
    """
    original_values = {}

    # Save original values and set new ones
    for name, value in env_vars.items():
        if name in os.environ:
            original_values[name] = os.environ[name]
        os.environ[name] = value

    try:
        yield
    finally:
        # Restore original values
        for name in env_vars:
            if name in original_values:
                os.environ[name] = original_values[name]
            else:
                del os.environ[name]

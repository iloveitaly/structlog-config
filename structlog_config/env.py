import os


TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


def get_env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def get_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    normalized_value = value.strip().lower()

    if normalized_value in TRUE_VALUES:
        return True

    if normalized_value in FALSE_VALUES:
        return False

    raise ValueError(f"Invalid boolean environment variable {name}={value!r}")

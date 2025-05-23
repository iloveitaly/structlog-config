from pathlib import Path

from structlog_config import configure_logger


def test_path_prettifier(capsys):
    base_dir = Path.cwd()

    log = configure_logger()
    log.info("message", key=base_dir / "test" / "file.txt")

    log_output = capsys.readouterr()

    assert "Path" not in log_output.out
    assert "path" in log_output.out

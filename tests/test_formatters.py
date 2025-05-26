from pathlib import Path, PosixPath

from structlog_config import configure_logger


def test_path_prettifier(capsys):
    base_dir = Path.cwd()

    log = configure_logger()
    log.info("message", key=base_dir / "test" / "file.txt")

    log_output = capsys.readouterr()

    assert "Path" not in log_output.out
    assert "path" not in log_output.out


def test_posixpath_prettifier(capsys):
    """
    Original problem was noticing this in the logs:

    2025-05-23 06:41:53 [info     ] direnv environment loaded and cached [test] direnv_state_file=PosixPath('tmp/direnv_state_7f752eb7bf8a5411b7c7d38449299e064b32b9264c15ef6a6943e88106b76f0c')
    """

    base_dir = PosixPath.cwd()

    log = configure_logger()
    log.info("message", key=base_dir / "test" / "file.txt")

    log_output = capsys.readouterr()

    assert "PosixPath" not in log_output.out
    assert "path" not in log_output.out

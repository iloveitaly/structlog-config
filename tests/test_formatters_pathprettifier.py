from pathlib import Path

from structlog_config.formatters import PathPrettifier


def test_path_prettifier_relative(tmp_path, monkeypatch):
    # Set up a fake CWD
    monkeypatch.chdir(tmp_path)
    base_dir = Path.cwd()
    rel_file = tmp_path / "foo.txt"
    rel_file.touch()
    event_dict = {"file": rel_file}
    prettifier = PathPrettifier(base_dir=base_dir)
    result = prettifier(None, None, event_dict.copy())
    # Should be relative path
    assert result["file"] == "foo.txt"


def test_path_prettifier_absolute(tmp_path):
    # Use a base_dir different from file's parent
    base_dir = tmp_path / "other"
    base_dir.mkdir()
    abs_file = tmp_path / "bar.txt"
    abs_file.touch()
    event_dict = {"file": abs_file}
    prettifier = PathPrettifier(base_dir=base_dir)
    result = prettifier(None, None, event_dict.copy())
    # Should be absolute path as string
    assert result["file"] == str(abs_file)


def test_path_prettifier_non_path():
    event_dict = {"foo": 123, "bar": "baz"}
    prettifier = PathPrettifier()
    result = prettifier(None, None, event_dict.copy())
    # Non-path values should be unchanged
    assert result == event_dict


def test_path_prettifier_multiple_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base_dir = Path.cwd()
    file1 = tmp_path / "a.txt"
    file2 = tmp_path / "b.txt"
    file1.touch()
    file2.touch()
    event_dict = {"file1": file1, "file2": file2}
    prettifier = PathPrettifier(base_dir=base_dir)
    result = prettifier(None, None, event_dict.copy())
    assert result["file1"] == "a.txt"
    assert result["file2"] == "b.txt"

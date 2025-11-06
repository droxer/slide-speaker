from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts import storage_cli


def test_redact_config_masks_sensitive_values() -> None:
    redacted = storage_cli._redact_config(
        {
            "bucket_name": "demo",
            "aws_secret_access_key": "super-secret",
            "apiToken": "token-value",
        }
    )
    assert redacted["bucket_name"] == "demo"
    assert redacted["aws_secret_access_key"] == "*****"
    assert redacted["apiToken"] == "*****"


def test_cmd_info_masks_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_config = SimpleNamespace(
        storage_provider="s3",
        storage_config={"aws_secret_access_key": "secret", "bucket_name": "bucket"},
    )
    monkeypatch.setattr(storage_cli, "config", fake_config)
    storage_cli.cmd_info(Namespace())
    out = capsys.readouterr().out
    assert "Active provider: s3" in out
    assert "*****" in out
    assert "bucket" in out


def test_cmd_exists_found(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = MagicMock()
    provider.file_exists.return_value = True
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    gather = AsyncMock(return_value=("file-1", ["outputs/foo.mp4"]))
    monkeypatch.setattr(storage_cli, "_gather_task_artifacts", gather)
    storage_cli.cmd_exists(Namespace(task_id="task-1", json=False))
    out = capsys.readouterr().out
    assert "Task task-1 (file_id=file-1)" in out
    assert "[FOUND] outputs/foo.mp4" in out
    gather.assert_awaited_once_with("task-1")
    provider.file_exists.assert_called_once_with("outputs/foo.mp4")


def test_cmd_exists_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = MagicMock()
    provider.file_exists.side_effect = [True, False]
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    gather = AsyncMock(return_value=("file-1", ["outputs/foo.mp4", "outputs/bar.mp4"]))
    monkeypatch.setattr(storage_cli, "_gather_task_artifacts", gather)
    with pytest.raises(SystemExit) as exc:
        storage_cli.cmd_exists(Namespace(task_id="task-1", json=False))
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "[FOUND] outputs/foo.mp4" in out
    assert "[MISSING] outputs/bar.mp4" in out
    assert "1 artifact(s) missing." in out


def test_cmd_exists_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = MagicMock()
    provider.file_exists.return_value = True
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    gather = AsyncMock(return_value=("file-7", ["outputs/audio/final.mp3"]))
    monkeypatch.setattr(storage_cli, "_gather_task_artifacts", gather)
    storage_cli.cmd_exists(Namespace(task_id="task-7", json=True))
    payload = capsys.readouterr().out
    assert '"task_id": "task-7"' in payload
    assert '"file_id": "file-7"' in payload
    assert '"key": "outputs/audio/final.mp3"' in payload


def test_cmd_exists_task_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = MagicMock()
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    gather = AsyncMock(side_effect=LookupError("Task 'task-9' not found."))
    monkeypatch.setattr(storage_cli, "_gather_task_artifacts", gather)
    with pytest.raises(SystemExit) as exc:
        storage_cli.cmd_exists(Namespace(task_id="task-9", json=False))
    assert exc.value.code == 1


def test_cmd_delete_force_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = MagicMock()
    provider.file_exists.return_value = False
    provider.delete_file.side_effect = FileNotFoundError()
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    storage_cli.cmd_delete(Namespace(object_key="foo", force=True))
    provider.delete_file.assert_called_once_with("foo")
    out = capsys.readouterr().out
    assert "already absent" in out


def test_cmd_delete_missing_without_force(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = MagicMock()
    provider.file_exists.return_value = False
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    with pytest.raises(SystemExit) as exc:
        storage_cli.cmd_delete(Namespace(object_key="foo", force=False))
    assert exc.value.code == 1


def test_cmd_upload_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = MagicMock()
    provider.upload_file.return_value = "s3://bucket/foo"
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    source = tmp_path / "input.txt"
    source.write_text("data")
    storage_cli.cmd_upload(
        Namespace(file_path=str(source), object_key="foo", content_type=None)
    )
    provider.upload_file.assert_called_once()
    out = capsys.readouterr().out
    assert "Uploaded" in out
    assert "s3://bucket/foo" in out


def test_cmd_upload_missing_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    provider = MagicMock()
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    with pytest.raises(SystemExit) as exc:
        storage_cli.cmd_upload(
            Namespace(
                file_path=str(tmp_path / "missing.txt"),
                object_key="foo",
                content_type=None,
            )
        )
    assert exc.value.code == 1
    provider.upload_file.assert_not_called()


def test_cmd_download_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = MagicMock()
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    destination = tmp_path / "out.dat"
    storage_cli.cmd_download(Namespace(object_key="foo", destination=str(destination)))
    provider.download_file.assert_called_once_with("foo", str(destination))
    out = capsys.readouterr().out
    assert "Downloaded" in out


def test_cmd_url_outputs_value(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = MagicMock()
    provider.get_file_url.return_value = "https://example.com/url"
    monkeypatch.setattr(storage_cli, "get_storage_provider", lambda: provider)
    storage_cli.cmd_url(
        Namespace(object_key="foo", expires=100, disposition=None, content_type=None)
    )
    provider.get_file_url.assert_called_once()
    out = capsys.readouterr().out.strip()
    assert out == "https://example.com/url"

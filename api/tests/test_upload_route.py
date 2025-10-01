import base64
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidespeaker.configs.config import config
from slidespeaker.core.task_queue import task_queue
from slidespeaker.routes.upload import router


@pytest.fixture()
def client(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(router)

    class DummyStorage:
        def upload_file(self, *args, **kwargs):
            return "storage://dummy"

    async def fake_submit_task(*args, **kwargs):
        return "task-123"

    monkeypatch.setattr(config, "_uploads_dir", Path(tmp_path))
    monkeypatch.setattr(config, "get_storage_provider", lambda: DummyStorage())
    monkeypatch.setattr(task_queue, "submit_task", fake_submit_task)

    return TestClient(app)


def test_multipart_upload(client):
    files = {
        "file": ("sample.pdf", b"dummy-data", "application/pdf"),
    }
    data = {
        "voice_language": "english",
        "video_resolution": "hd",
        "generate_avatar": "true",
        "generate_subtitles": "true",
        "generate_podcast": "false",
        "generate_video": "true",
        "task_type": "video",
        "source_type": "pdf",
    }

    response = client.post("/api/upload", data=data, files=files)
    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "task-123"
    assert payload["file_id"]


def test_json_upload_with_data_url(client):
    file_bytes = b"dummy-ppt"
    encoded = base64.b64encode(file_bytes).decode("ascii")
    data_url = f"data:application/vnd.openxmlformats-officedocument.presentationml.presentation;base64,{encoded}"

    response = client.post(
        "/api/upload",
        json={
            "filename": "deck.pptx",
            "file_data": data_url,
            "voice_language": "english",
            "video_resolution": "hd",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "task-123"
    assert payload["file_id"]


def test_json_upload_plain_base64(client):
    file_bytes = b"dummy-podcast"
    encoded = base64.b64encode(file_bytes).decode("ascii")

    response = client.post(
        "/api/upload",
        json={
            "filename": "audio.mp3",
            "file_data": encoded,
            "voice_language": "english",
            "video_resolution": "hd",
            "generate_podcast": True,
            "generate_video": False,
            "task_type": "podcast",
            "source_type": "pdf",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "task-123"
    assert payload["file_id"]

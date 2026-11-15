import asyncio
import os
import sys
from pathlib import Path

import asyncpg
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["INKLOOM_ENGINE"] = "builtin"


@pytest.fixture(autouse=True)
def cleanup_test_submissions(monkeypatch):
    submission_ids = []
    original_post = TestClient.post

    def track_submission(client, url, *args, **kwargs):
        response = original_post(client, url, *args, **kwargs)
        if url == "/api/submissions" and response.status_code == 200:
            submission_ids.append(response.json()["id"])
        return response

    monkeypatch.setattr(TestClient, "post", track_submission)
    yield

    if submission_ids:
        database_url = os.environ["DATABASE_URL"]

        async def cleanup():
            conn = await asyncpg.connect(dsn=database_url)
            try:
                await conn.execute(
                    "DELETE FROM submissions WHERE id = ANY($1::BIGINT[])",
                    submission_ids,
                )
            finally:
                await conn.close()

        asyncio.run(cleanup())

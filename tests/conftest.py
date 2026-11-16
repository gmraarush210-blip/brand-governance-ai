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
def cleanup_test_submissions(monkeypatch, request):
    submission_ids = []
    original_post = TestClient.post
    test_database_url = None

    if request.module.__name__.endswith("test_api"):
        test_database_url = os.getenv("TEST_DATABASE_URL")
        if not test_database_url:
            pytest.skip("Set TEST_DATABASE_URL to a dedicated test database before running API tests")
        production_database_url = os.getenv("DATABASE_URL")
        if production_database_url and test_database_url == production_database_url:
            pytest.fail("TEST_DATABASE_URL must not be the configured DATABASE_URL")
        monkeypatch.setenv("DATABASE_URL", test_database_url)

    def track_submission(client, url, *args, **kwargs):
        response = original_post(client, url, *args, **kwargs)
        if url == "/api/submissions" and response.status_code == 200:
            submission_ids.append(response.json()["id"])
        return response

    monkeypatch.setattr(TestClient, "post", track_submission)
    yield

    if submission_ids and test_database_url:
        database_url = test_database_url

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

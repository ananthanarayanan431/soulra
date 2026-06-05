import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_run_ingestion_task_marks_job_failed_when_pipeline_raises_and_row_missing():
    """scalar_one() in error path raises NoResultFound if row missing → job stuck in processing.
    After fix: scalar_one_or_none() + None guard means missing row is handled gracefully."""
    from soulra.api.v1.ingest import _run_ingestion_task

    job_id = uuid.uuid4()

    # Mock session that returns None for the job row (simulates missing/deleted row)
    mock_session = AsyncMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = None  # row not found
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_factory = MagicMock(return_value=mock_session)
    mock_eng = AsyncMock()
    mock_eng.dispose = AsyncMock()

    with patch("soulra.api.v1.ingest.create_async_engine", return_value=mock_eng), \
         patch("soulra.api.v1.ingest.async_sessionmaker", return_value=mock_session_factory), \
         patch("soulra.api.v1.ingest._get_pipeline") as mock_pipeline_factory:
        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(side_effect=Exception("pipeline failed"))
        mock_pipeline_factory.return_value = mock_pipeline

        # Should NOT raise — NoResultFound in error path must be handled gracefully
        await _run_ingestion_task(b"content", "test.pdf", {}, job_id)


@pytest.mark.asyncio
async def test_run_ingestion_task_uses_scalar_one_or_none_in_success_path():
    """scalar_one() in success path should be scalar_one_or_none() to handle edge cases."""
    from soulra.api.v1.ingest import _run_ingestion_task

    job_id = uuid.uuid4()

    mock_row = MagicMock()
    mock_session = AsyncMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_row
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_factory = MagicMock(return_value=mock_session)
    mock_eng = AsyncMock()
    mock_eng.dispose = AsyncMock()

    with patch("soulra.api.v1.ingest.create_async_engine", return_value=mock_eng), \
         patch("soulra.api.v1.ingest.async_sessionmaker", return_value=mock_session_factory), \
         patch("soulra.api.v1.ingest._get_pipeline") as mock_pipeline_factory:
        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(return_value={"chunks_created": 3, "tokens_used": 0})
        mock_pipeline_factory.return_value = mock_pipeline

        await _run_ingestion_task(b"content", "test.pdf", {"tradition": "stoic"}, job_id)

    # Verify scalar_one_or_none was used (not scalar_one)
    assert mock_execute_result.scalar_one_or_none.called, \
        "scalar_one_or_none() should be used instead of scalar_one()"
    assert not mock_execute_result.scalar_one.called, \
        "scalar_one() must not be used — it raises NoResultFound if row is missing"

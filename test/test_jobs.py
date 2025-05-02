import os
import sys
import pytest
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from jobs import add_job, update_job_status, process_job

@patch("jobs.redis")
@patch("jobs.hotqueue")
def test_add_job(mock_hotqueue, mock_redis):
    mock_redis_instance = mock_redis.Redis.return_value
    mock_queue = mock_hotqueue.HotQueue.return_value
    job_id = add_job("2001-01-01", "2001-12-31")
    assert isinstance(job_id, str)
    assert mock_redis_instance.hmset.called
    assert mock_queue.put.called

@patch("jobs.redis.Redis")
def test_update_job_status(mock_redis_class):
    mock_redis = mock_redis_class.return_value
    update_job_status("job_id", "completed")
    mock_redis.hset.assert_called_with("job.job_id", "status", "completed")

@patch("jobs.redis.Redis")
def test_process_job(mock_redis_class):
    mock_redis = mock_redis_class.return_value
    mock_redis.hgetall.return_value = {
        b"start": b"2001-01-01",
        b"end": b"2001-12-31",
        b"status": b"submitted"
    }
    process_job("job_id")
    assert mock_redis.hset.called

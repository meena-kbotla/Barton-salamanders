import sys
import os
import pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from worker import process_job

@patch("worker.process_job")
@patch("worker.update_job_status")
def test_job_worker_success(mock_update, mock_process):
    job_worker("test-id")
    mock_process.assert_called_once_with("test-id")
    mock_update.assert_called_once_with("test-id", "completed")

@patch("worker.process_job", side_effect=Exception("fail"))
@patch("worker.update_job_status")
def test_job_worker_failure(mock_update, mock_process):
    job_worker("bad-id")
    mock_process.assert_called_once_with("bad-id")
    mock_update.assert_called_once_with("bad-id", "failed")

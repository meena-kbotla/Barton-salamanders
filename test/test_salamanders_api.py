import sys
import os
import json
import pytest
from flask import Flask
from flask.testing import FlaskClient
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from salamanders_api import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200

def test_jobs_post_missing_params(client):
    response = client.post("/jobs", json={})
    assert response.status_code == 400
    assert b"Missing required parameters" in response.data

def test_jobs_post_success(client, monkeypatch):
    def mock_add_job(start, end):
        return "mock-job-id"

    monkeypatch.setattr("salamanders_api.add_job", mock_add_job)
    response = client.post("/jobs", json={"start": "2001-01-01", "end": "2001-12-31"})
    assert response.status_code == 202
    assert b"mock-job-id" in response.data

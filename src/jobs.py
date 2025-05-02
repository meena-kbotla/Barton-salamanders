import json
from uuid import uuid4
import redis
import os
import logging
from datetime import datetime
from hotqueue import HotQueue

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Use env vars with fallback defaults
REDIS_HOST = os.getenv("REDIS_HOST", "redis-db")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Redis clients
rd = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1)  # result store
jdb = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2)  # job metadata
q = HotQueue("job_queue", host=REDIS_HOST, port=REDIS_PORT, db=2)  # job queue

def _generate_jid():
    """
    Generate a pseudo-random identifier for a job.

    Returns:
        str: a unique job identifier
    """
    return str(uuid4())

def _instantiate_job(jid, status, start, end):
    """
    Create the job object description as a python dictionary. Requires the job id,
    status, start and end parameters.

    Args:
        jid (str): Job ID
        status (str): Job Status ("submitted", "in progress", etc.)
        start (str): Start of some processing range
        end (str): End of some processing range

    Returns:
        dict: the job description
    """
    return {'id': jid,
            'status': status,
            'start': start,
            'end': end }

def _save_job(jid, job_dict):
    """
    Save a job object in the Redis database.

    Args:
        jid (str): Job ID
        job_dict (dict): Job data to store
    """
    jdb.set(f"job:{jid}", json.dumps(job_dict))
    logger.info(f"Saved job {jid} in Redis.")
    return

def _queue_job(jid):
    """
    Add a job to the redis queue.

    Args:
        jid (str): Job ID
    """
    if jid is None:
    logger.error("Attempted to queue a job with None as the job ID.")
    q.put(jid)
    logger.info(f"Job {jid} added to queue.")
    return

def add_job(year, month):
    """
    Add a job to the redis queue.
    
    Args:
        start (str): Start of range
        end (str): End of range
        status (str): Initial status (default "submitted")

    Returns:
        dict: The job dictionary
    """
    print("INSIDE add_job()")
    job_id = str(uuid4())

    job_data = {
        "id": job_id,
        "status": "submitted",
        "year": year,
        "month": month,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Save the job metadata in Redis
    _save_job(job_id, job_data)

    # Queue the job for processing
    logger.info("Pushing job ID {job_id} to the queue.")
    _queue_job(job_id)
    
    return job_id

def get_job_by_id(jid):
    """
    Return job dictionary given jid
    
    Args:
        jid (str): Job ID

    Returns:
        dict: Job data
    """
    job_data = jdb.get(f"job:{jid}")
    if job_data:
        job_data = json.loads(job_data)
        results = rd.get(f"result:{jid}")
        if results:
            job_data["summary"] = json.loads(result)
        return job_data
    return None

def update_job_status(job_id, status):
    """
    Update the status of job with job id `jid` to status `status`.
    
    Args:
        job_id (str): Job ID
        status (str): New status value

    Raises: 
        Exception: if job is not found
    """
    job_data = jdb.get(f"job:{job_id}")
    if job_data:
        job_data = json.loads(job_data)
        job_data['status'] = status
        jdb.set(f"job:{job_id}", json.dumps(job_data))
        logger.info(f"Updated job {job_id} status to {status}.")
    else:
        logger.error(f"Job ID {job_id} not found in the database.")
        raise ValueError (f"Job ID {job_id} not found")

def list_jobs() -> list:
    """
    Lists all stored job IDS from Redis with a job.* key pattern.

    There is no input arguments.

    Returns:
        keys (list): lists all stored job IDs
    """
    keys = jdb.keys("job.*")
    return [key.split(".")[1] for key in keys]

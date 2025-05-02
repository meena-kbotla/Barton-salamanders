import json
import uuid
import redis
import os
from datetime import datetime
from hotqueue import HotQueue

_redis_ip='redis-db'
_redis_port='6379'

rd = redis.Redis(host=_redis_ip, port=6379, db=1)
q = HotQueue("queue", host=_redis_ip, port=6379, db=2)
jdb = redis.Redis(host=_redis_ip, port=6379, db=2)

def _generate_jid():
    """
    Generate a pseudo-random identifier for a job.

    Returns:
        str: a unique job identifier
    """
    return str(uuid.uuid4())

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
    jdb.set(jid, json.dumps(job_dict))
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
    job_id = _generate_jid()

    job_data = {
        "id": job_id,
        "status": "submitted",
        "year": year,
        "month": month,
        "timestamp": datetime.utcnow().isoformat()
    }

    jdb.set(f"job:{job_id}", json.dumps(job_data))

    # Queue the job for processing
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
    job = rd.hgetall(f"job:{jid}")
    results = rs.get(f"result:{jid}")
    if result:
        job["summary"] = json.loads(result)
    return job

def update_job_status(jid, status):
    """
    Update the status of job with job id `jid` to status `status`.
    
    Args:
        jid (str): Job ID
        status (str): New status value

    Raises: 
        Exception: if job is not found
    """
    job_rd = redis.Redis(host='redis-db', port=6379, db=2)  # Use the correct Redis DB

    job_data = job_rd.get(f"job:{job_id}")
    if job_data:
        job_data = json.loads(job_data)
        job_data['status'] = status
        job_rd.set(f"job:{job_id}", json.dumps(job_data))
    else:
        raise ValueError (f"Job ID {job_id} not found")

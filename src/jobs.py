import json
import uuid
import redis
from hotqueue import HotQueue

_redis_ip='redis-db'
_redis_port='6379'

rd = redis.Redis(host=_redis_ip, port=6379, db=0)
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

def add_job(start, end, status="submitted"):
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

    # Check that start and end are provided and valid
    if not start or not end:
        raise ValueError("Both 'start' and 'end' are required for a job.")

    # Create the job object (e.g., status: "submitted", you can change the status later)
    job_dict = _instantiate_job(job_id, "submitted", start, end)

    # Save the job object in Redis
    _save_job(job_id, job_dict)
    
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
    return json.loads(jdb.get(jid))

def process_job(job_id: str):
    """
    Simulate the processing of a salamander job.

    Args:
        job_id (str): The job identifier to process.
    """
    print(f"Processing job {job_id}")

    job_key = f"job.{job_id}"
    job_data = db.hgetall(job_key)

    if not job_data:
        raise ValueError(f"Job ID {job_id} not found in Redis.")

    try:
        # Decode bytes to strings
        start = job_data[b"start"].decode("utf-8")
        end = job_data[b"end"].decode("utf-8")
    except KeyError as e:
        raise ValueError(f"Missing required job field: {e}")

    # Simulate processing result (replace this with real logic)
    result_data = {
        "summary": f"Processed salamander data from {start} to {end}",
        "count": 42,
        "start": start,
        "end": end
    }

    # Store result as JSON string in Redis under the same job hash
    db.hset(job_key, mapping={"result": json.dumps(result_data)})

    print(f"Finished processing job {job_id}")

def update_job_status(jid, status):
    """
    Update the status of job with job id `jid` to status `status`.
    
    Args:
        jid (str): Job ID
        status (str): New status value

    Raises: 
        Exception: if job is not found
    """
    job_dict = get_job_by_id(jid)
    if job_dict:
        job_dict['status'] = status
        _save_job(jid, job_dict)
    else:
        raise Exception(f"JOB ID {jid} not found.")

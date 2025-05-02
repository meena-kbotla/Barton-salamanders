import redis
import time
import json
from hotqueue import HotQueue
from jobs import update_job_status, get_job_by_id


# Redis clients
rd = redis.Redis(host="redis-db", port=6379, db=0)
q = HotQueue("queue", host="redis-db", port=6379, db=2)

def process_job(job):
    """
    Simulates processing of a job.

    Args:
        job (dict): The job data

    Returns:
        dict: The result
    """
    print(f"[WORKER] Processing job {job['id']}")
    time.sleep(2) # simulate processing delay
    result = {
        "job_id": job["id"],
        "result": f"Processed data from {job['start']} to {job['end']}"
    }
    return result

def save_result(job_id, result):
    """
    Save result into Redis.

    Args:
        job_id (str): Job ID
        result (dict): Result to save
    """
    key = f"result:{job_id}"
    rd.set(key, json.dumps(result))

print("Worker started. Waiting for jobs...")

while True:
    jid = q.get() # blocks until job is available
    if jid:
        job = get_job_by_id(jid)
        if job:
            update_job_status(jid, "in progress")
            result = process_job(job)
            save_result(jid, result)
            update_job_status(jid, "complete")

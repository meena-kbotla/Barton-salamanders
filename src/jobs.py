import json
import uuid
import redis
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime
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

def process_job(job_id: str):
    """
    Simulate the processing of a job, generate a plot, and store the image in Redis.

    Args:
        job_id (str): The job identifier to process.
    """
    try:
        logger.info(f"Processing job {job_id}")
        
        # Retrieve job data from Redis
        job_data = rd.hgetall(f"job.{job_id}")
        if not job_data:
            logger.error(f"Job data for {job_id} not found.")
            return

        start = job_data[b"start"].decode()
        end = job_data[b"end"].decode()

        # Log the received job data
        logger.info(f"Job {job_id} has start: {start} and end: {end}")

        # Load data from the dataset URL
        url = "https://data.austintexas.gov/resource/brj7-e355.json"
        df = pd.read_json(url)

        # Ensure "year_month" is in datetime format
        df['year_month'] = pd.to_datetime(df['year_month'], format='%Y-%m-%dT%H:%M:%S.%f')

        # Filter data based on the start and end dates
        filtered_df = df[(df['year_month'] >= start) & (df['year_month'] <= end)]

        if filtered_df.empty:
            logger.error(f"No data found for job {job_id} within date range {start} - {end}")
            rd.hset(f"job.{job_id}", "status", "failed")
            return

        # Generate the plot (for example, a histogram of some relevant column, say 'value')
        fig, ax = plt.subplots()
        filtered_df["value"].hist(ax=ax)  # Replace "value" with the appropriate column name
        ax.set_title(f"Data Distribution ({start} to {end})")
        
        # Save the plot as an image
        image_path = f"/data/{job_id}.png"
        fig.savefig(image_path)
        logger.info(f"Plot saved as {image_path}")
        
        # Store the image path in Redis under the job ID
        rd.hset(f"job.{job_id}", "result", image_path)
        rd.hset(f"job.{job_id}", "status", "completed")
        
        logger.info(f"Job {job_id} completed successfully and result saved.")
    
    except Exception as e:
        logger.error(f"Failed to process job {job_id}: {e}")
        rd.hset(f"job.{job_id}", "status", "failed")

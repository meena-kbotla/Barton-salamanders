import logging
from jobs import update_job_status, process_job
from hotqueue import HotQueue
import os

# Redis configuration
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
q = HotQueue("job_queue", host=redis_host, port=redis_port, db=1)

# Set up logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@q.worker
def job_worker(job_id: str, *args):
    """
    Simulates a background worker that processes the job and
    updates status from "in progress" to "completed"

    Arguments:
        job_id (str): specific job ID
    """
    if not job_id:
        logger.error(f"Received invalid job ID: {job_id}")
        return  # Skip processing if job ID is invalid
    
    logger.info(f"Worker picked up job: {job_id}")
    
    try:
        process_job(job_id)
        update_job_status(job_id, "completed")
    except Exception as e:
        logger.error(f"Failed to process job {job_id}: {e}")
        update_job_status(job_id, "failed")
        return

    logger.info(f"Job {job_id} completed successfully")


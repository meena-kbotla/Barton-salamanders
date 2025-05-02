import logging
import os
import json
import redis
import time
from hotqueue import HotQueue
from jobs import update_job_status

# Use env vars with fallback defaults
REDIS_HOST = os.getenv("REDIS_HOST", "redis-db")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Redis clients
rd = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1)  # result store
jdb = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2)  # job metadata
q = HotQueue("job_queue", host=REDIS_HOST, port=REDIS_PORT, db=2)  # job queue

# Set up logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@q.worker
def job_worker(job_id: str):
    try:
        logger.info(f"Received job: {job_id}")
        data = rd.get(f"job:{job_id}")
        if data is None:
            logger.error(f"No job data found for job ID {job_id}")
            return
        job_data = json.loads(data)
        process_job(job_id, job_data)
    except Exception as e:
        logger.exception(f"Unhandled exception in job_worker for job {job_id}: {e}")

print("Worker is running and listening for jobs...")
while True:
    time.sleep(1)  # Prevent container from exiting

def process_job(job_id, job_data):
    logger.info(f"Starting job {job_id}")
    year = job_data.get("year")
    month = job_data.get("month")
    key = "raw-data"

    update_job_status(job_id, "in progress")

    if not rd.exists(key):
        error_msg = {"status": "failed", "reason": "No dataset found"}
        rd.set(f"result:{job_id}", json.dumps(error_msg))
        logger.error(f"Job {job_id} failed: {error_msg['reason']}")
        return

    dataset = json.loads(rd.get(key))
    filtered = [entry for entry in dataset if entry["year_month"].startswith(f"{year}-{month}")]

    total_count = 0
    discharge_sum = 0
    discharge_count = 0
    total_filalgae = 0
    total_sedcov = 0

    for entry in filtered:
        for k in [
            "parthenia_juvenile", "parthenia_subadult", "parthenia_adult",
            "eliza_juvenile", "eliza_subadult", "eliza_adult"
        ]:
            val = entry.get(k)
            if val and val != "NA":
                try:
                    total_count += int(val)
                except ValueError:
                    pass

        discharge = entry.get("discharge_bs")
        if discharge and discharge != "NA":
            try:
                discharge_sum += float(discharge)
                discharge_count += 1
            except ValueError:
                pass

        for fa_key in ["parthenia_filalgae", "eliza_filalgae"]:
            fa_val = entry.get(fa_key)
            if fa_val and fa_val != "NA":
                try:
                    total_filalgae += float(fa_val)
                except ValueError:
                    pass

        for sc_key in ["parthenia_sedcov", "eliza_sedcov"]:
            sc_val = entry.get(sc_key)
            if sc_val and sc_val != "NA":
                try:
                    total_sedcov += float(sc_val)
                except ValueError:
                    pass

    average_discharge = round(discharge_sum / discharge_count, 2) if discharge_count else None

    result = {
        "job_id": job_id,
        "status": "completed",
        "summary": {
            "total_count": total_count,
            "year": year,
            "month": month,
            "average_discharge": average_discharge,
            "total_filalgae": round(total_filalgae, 2),
            "total_sedcov": round(total_sedcov, 2)
        }
    }

    rd.set(f"result:{job_id}", json.dumps(result))
    update_job_status(job_id, "completed")
    logger.info(f"Job {job_id} completed.")


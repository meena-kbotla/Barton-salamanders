import logging
from jobs import update_job_status
from hotqueue import HotQueue
import os

# Redis configuration
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
q = HotQueue("job_queue", host=redis_host, port=redis_port, db=2)

# Set up logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def process_job(job_id, job_data):
    year = job_data.get("year")
    month = job_data.get("month")
    key = "raw-data"
    
    update_job_status(job_id, "in progress")

    if not r.exists(key):
        r.set(f"result:{job_id}", json.dumps({"status": "failed", "reason": "No dataset found"}))
        return

    dataset = json.loads(r.get(key))
    filtered = [entry for entry in dataset if entry["year_month"].startswith(f"{year}-{month}")]

    total_count = 0
    discharge_sum = 0
    discharge_count = 0
    total_filalgae = 0
    total_sedcov = 0

    for entry in filtered:
        # Count all valid numerical salamander values
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

        # Discharge
        discharge = entry.get("discharge_bs")
        if discharge and discharge != "NA":
            try:
                discharge_sum += float(discharge)
                discharge_count += 1
            except ValueError:
                pass

        # Filalgae
        for fa_key in ["parthenia_filalgae", "eliza_filalgae"]:
            fa_val = entry.get(fa_key)
            if fa_val and fa_val != "NA":
                try:
                    total_filalgae += float(fa_val)
                except ValueError:
                    pass

        # Sediment cover
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

    r.set(f"result:{job_id}", json.dumps(result))

    update_job_status(job_id, "completed")

@q.worker
def job_worker(job_id: str):
    """
    Simulates a background worker that processes the job and
    updates status from "in progress" to "completed"

    Arguments:
        job_id (str): specific job ID
    """
    print(f"Processing job: {job_id}")
    job_data = json.loads(r.get(f"job:{job_id}"))
    process_job(job_id, job_data)

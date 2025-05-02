import redis
import time
import pickle
import json

r = redis.Redis(host="redis-db", port=6379, db=0)

print("Worker started. Waiting for jobs...")

def process_job(job):
    # Simulate processing
    print(f"Processing job: {job}")
    time.sleep(2)
    result = {"job_id": job["job_id"], "result": f"Processed {job['data']}"}
    return result

while True:
    job_data = r.lpop("job-queue")
    if job_data:
        job = pickle.loads(job_data)
        result = process_job(job)
        r.set(f"result:{job['job_id']}", pickle.dumps(result))
    else:
        time.sleep(1)


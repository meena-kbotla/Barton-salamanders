import redis
import os
import requests
import json
import uuid
import logging
from flask import Flask
from flask import jsonify
from flask import request
from jobs import add_job, get_job_by_id, jdb

app = Flask(__name__)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

redis_host = os.environ.get('REDIS_HOST', 'localhost')

def get_redis_client():
    return redis.Redis(host='redis-db', port=6379, db=1)

def get_job_redis():
    return redis.Redis(host='redis-db', port=6379, db=2)

def get_results_redis():
    return redis.Redis(host='redis-db', port=6379, db=3)

def loading_redis():
    rd = redis.Redis(host=redis_host, port=6379, db=0)

    if not rd.exists('data'):
        url = "https://data.austintexas.gov/resource/brj7-e355.json"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            rd.set('data', json.dumps(data))
        except Exception as e:
            print(f"Error loading data from URL: {e}")
            return None

    return rd

@app.route('/help')
def help():
    return jsonify({
        "/help": "GET - list all available endpoints",
        "/data": "POST/GET/DELETE - handle salamander dataset (auto-downloads from city)",
        "/genes": "GET - list all hgnc IDs (from HGNC dataset)",
        "/genes/<hgnc_id>": "GET - get gene by ID",
        "/jobs/<job_id>": "GET - job status",
        "/results/<job_id>": "GET - retrieve image or job result"
    })

#/data: post, get, delete
#post: posts data to redis container
#get: prints data from redis container
#delete: deletes data from redis container
@app.route('/data', methods=['POST', 'GET', 'DELETE'])
def data_route():
    '''
    This function handles the data stored in the Redis container
    Args:
        POST(method)
        GET(method)
        DELETE(method)

    Returns:
        Dataset is posted to the Redis container
        Dataset is returned
        Dataset is removed from the Redis container
    '''
    rd = loading_redis()
    if rd is None:
        retunr jsonify({"error": "Failed to load data"}), 500

    if request.method == 'POST':
        return jsonify({"message": "Data is auto-loaded from URL and stored in Redis on first use."})

    elif request.method == 'GET':
        return json.loads(rd.get('data'))

    elif request.method == 'DELETE':
        rd.delete('data')
        return jsonify({"message": "Data deleted from Redis."})

#/genes: get
#/genes: prints all of the hgnc_ids from the dataset
#/genes/<hgnc_id>: prints all the data corresponding to a specific hgnc_id
@app.route('/genes', methods=['GET'])
@app.route('/genes/<hgnc_id>', methods=['GET'])
def genes_route(hgnc_id=None):
    '''
    This function outputs the data based on hgnc_id
    Args:
        hgnc_id(str): the hgnc_id corresponding to a chunk of data

    Returns:
        ids: all the hgnc ids from the dataset, returned when hgnc_id is not specified
        data: all the data corresponding to a given hgnc_id, returned with the hgnc_id is specified
    '''
    rd = loading_redis()
    data = json.loads(rd.get('data'))
    if hgnc_id is not None:
        if isinstance(hgnc_id, str):
            for i in range(0, len(data['response']['docs'])):
                the_id = data['response']['docs'][i]['hgnc_id']
                if hgnc_id == the_id:
                    return data['response']['docs'][i]
        else:
            return f"The input is not a string!"
    else:
        ids = []
        for i in range(0, len(data['response']['docs'])):
            ids.append(data['response']['docs'][i]['hgnc_id'])
        return jsonify(ids)

@app.route('/jobs', methods=['GET'])
@app.route('/jobs', methods=['POST'])
@app.route('/jobs/<job_id>', methods=['GET'])
def jobs_route(job_id=None):
    '''
    This function creates job ids, outputs all job ids, or outputs data related to a specific job id
    '''
    rd = loading_redis()
    job_rd = get_job_redis()

    if job_id is None:
        if request.method == 'POST':
            inputt = request.get_json()
            hgnc_start = inputt.get('hgnc_start')
            hgnc_end = inputt.get('hgnc_end')

            if not hgnc_start or not hgnc_end:
                return jsonify({"error": "Missing required parameters: 'hgnc_start' and 'hgnc_end'"})
            start_num = int(hgnc_start)
            end_num = int(hgnc_end)
            job = add_job(start_num, end_num)

            return jsonify({"job_id": job["id"]})

        elif request.method == 'GET':
            keys = jdb.keys()
            return jsonify([key.decode('utf-8') for key in keys])

    else:
        data = job_rd.get(job_id)
        if data is None:
            return jsonify({"error": "Job ID not found"})
        return jsonify(json.loads(data))

@app.route('/results/<job_id>', methods=['GET'])
def results_route(job_id=None):
    '''
    This function take sin a job id and outputs data for the genes with hgnc_ids within the provided range.
    '''
    job_rd = get_job_redis()
    result_rd = get_results_redis()

    if not job_id:
        logger.warning(f"Job ID must be provided")
        return jsonify({"error": "Job ID must be provided"})

    result_data = result_rd.get(job_id)
    if result_data:
        return jsonify(json.loads(result_data))

    job_data = job_rd.get(job_id)
    if job_data:
        job_data = json.loads(job_data)
        if job_data['status'] == 'complete':
            return jsonify({"status": "Job is complete!"})
        else:
            return jsonify({"status": "Job is still processing!"})
    else:
        logger.warning(f"Job ID {job_id} not found")
        return jsonify({"error": "Invalid Job ID"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

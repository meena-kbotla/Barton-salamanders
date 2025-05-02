import redis
import os
import requests
import json
import uuid
import logging
import jobs
from flask import Flask
from flask import jsonify
from flask import request
from jobs import add_job, get_job_by_id, jdb, q
from collections import defaultdict


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

#/help: get
#/help: lists all available endpoints and their functions
@app.route('/help', methods=['GET'])
def help():
    return jsonify({
        "/help": "GET - list all available endpoints",
        "/data": "POST/GET/DELETE - handle salamander dataset (auto-downloads from Austin city data)",
        "/salamanders": "GET - list all recorded salamander sizes",
        "/salamanders/years": "GET - list all years in the dataset",
        "/salamanders/months/<year>": "GET - list months for a given year",
        "/salamanders/conditions/<year>/<month>": "GET - list all data for a given year and month",
        "/salamanders/sizes/<year>/<month>": "GET - size distribution for a given year and month",
        "/jobs": "GET/POST - submit a job request or list job IDs",
        "/jobs/<job_id>": "GET - job status and info",
        "/results/<job_id>": "GET - retrieve result of completed job"
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
        return jsonify({"error": "Failed to load data"}), 500

    if request.method == 'POST':
        return jsonify({"message": "Data is auto-loaded from URL and stored in Redis on first use."})

    elif request.method == 'GET':
        return json.loads(rd.get('data'))

    elif request.method == 'DELETE':
        rd.delete('data')
        return jsonify({"message": "Data deleted from Redis."})

#/salamanders: get
#/salamanders: returns all recorded sizes in the dataset
@app.route('/salamanders', methods=['GET'])
def get_all_salamanders():
    '''
    Returns all recorded sizes in the dataset
    '''
    rd = loading_redis()
    data = json.loads(rd.get('data'))

    size_values = {  # initialize sets to store unique values
        'eliza_adult': set(),
        'eliza_juvenile': set(),
        'eliza_subadult': set(),
        'parthenia_adult': set(),
        'parthenia_juvenile': set(),
        'parthenia_subadult': set()
    }

    for obs in data:
        for key in size_values:
            value = obs.get(key)
            if value not in ['NA', None, '']:
                try:
                    size_values[key].add(float(value))  # use float for numeric sorting
                except ValueError:
                    continue  # skip bad data

    # Convert sets to sorted lists
    sorted_size_values = {key: sorted(list(values)) for key, values in size_values.items()}

    return jsonify({
        "unique_sizes_sorted_by_key": sorted_size_values,
    })

#/salamanders/years: get
#/salamanders/years: returns a list of all unique years in the dataset
@app.route('/salamanders/years', methods=['GET'])
def get_all_years():
    '''
    Returns a list of unique years in the dataset
    '''
    rd = loading_redis()
    data = json.loads(rd.get('data'))
    years = sorted(set(entry['year_month'][:4] for entry in data if 'year_month' in entry))
    return jsonify(years)

#/salamanders/months/<year>: get
#/salamanders/months/<year>: returns all months for a given year
@app.route('/salamanders/months/<year>', methods=['GET'])
def get_months_by_year(year):
    '''
    Returns a list of months present in a given year
    Args:
        year (str): Year to search
    '''
    rd = loading_redis()
    data = json.loads(rd.get('data'))
    months = sorted(set(entry['year_month'][5:7] for entry in data if entry['year_month'][:4] == year))
    return jsonify(months)

#/salamanders/conditions/<year>/<month>: get
#/salamanders/conditions/<year>/<month>: returns salamander data for a specific year and month
@app.route('/salamanders/conditions/<year>/<month>', methods=['GET'])
def get_conditions_by_date(year, month):
    '''
    Returns all salamander data for a given year and month
    Args:
        year (str)
        month (str)
    '''
    rd = loading_redis()
    data = json.loads(rd.get('data'))
    results = [entry for entry in data if entry['year_month'][:4] == year and entry['year_month'][5:7] == month]
    return jsonify(results)

#/salamanders/sizes/<year>/<month>: get
#/salamanders/sizes/<year>/<month>: returns the salamander sizes for a year and month
@app.route('/salamanders/sizes/<year>/<month>', methods=['GET'])
def get_size_distribution(year, month):
    '''
    Returns a dictionary of salamander sizes and their counts for a specific year and month
    Args:
        year (str)
        month (str)
    '''
    rd = loading_redis()
    data = json.loads(rd.get('data'))

    size_counts = defaultdict(int)  # Default dict to automatically handle missing keys

    # Filter by year and month
    filtered_data = [entry for entry in data if entry.get('year_month', '')[:4] == year and entry.get('year_month', '')[5:7] == month]
    
    # Check if any data exists for the filtered year and month
    if not filtered_data:
        return jsonify({"message": "No data found for the given year and month"}), 404

    # Size keys based on your data
    size_keys = [
        'eliza_adult', 'eliza_juvenile', 'eliza_subadult', 
        'parthenia_adult', 'parthenia_juvenile', 'parthenia_subadult'
    ]
    
    for entry in filtered_data:
        for key in size_keys:
            if entry.get(key) not in ['NA', None, '']:  # Use `get` to avoid key errors
                size_counts[key] += float(entry[key])

    return jsonify(size_counts)

@app.route('/jobs', methods=['GET'])
@app.route('/jobs', methods=['POST'])
@app.route('/jobs/<job_id>', methods=['GET'])
def jobs_route(job_id=None):
    '''
    Creates a job for salamander data analysis, lists all job IDs, or shows info for a specific job ID
    '''
    job_rd = get_redis_client()

    if job_id is None:
        if request.method == 'POST':
            input_data = request.get_json()

            year = input_data.get('year')
            month = input_data.get('month')

            if not year or not month:
                return jsonify({"error": "Missing required parameters: 'year' and 'month'"}), 400

            try:
                job_id = add_job(year, month)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

            return jsonify({"job_id": job_id}), 202

        elif request.method == 'GET':
            job_ids = jdb.keys("job:*")  # Get all keys that start with "job:"
            job_ids = [job_id.decode("utf-8").split(":")[1] for job_id in job_ids]  # Strip the "job:" prefix
            return jsonify({"job_ids": job_ids})
    else:
        data = jobs.get_job_by_id(job_id)
        if data is None:
            return jsonify({"error": "Job ID not found"}), 404
        return jsonify(data)

@app.route('/results/<job_id>', methods=['GET'])
def results_route(job_id=None):
    '''
    Returns the results for a completed salamander data job by job_id.
    '''
    job_data = jobs.get_job_by_id(job_id)
    if not job_data:
        return jsonify({"error": "Job not found"}), 404

    status = job_data.get("status")
    if status != "completed":
        return jsonify({"message": f"Job status: {status}. Results not available yet."}), 202

    result = jobs.get_job_result(job_id)
    if result is None:
        return jsonify({"error": "Result not found"}), 404

    return jsonify(result), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

# Variables
IMAGE_NAME = dtrevino0630/ml_app
TAG = 1.0
CONTAINER_NAME = flask-app
REDIS_SERVICE = redis-db
FLASK_PORT = 5000
WORKER_NAME = worker

# Default target
.PHONY: all
all: build push deploy

# Build Docker images for Flask app, Redis, and Worker
.PHONY: build
build:
	IMAGE_NAME=$(IMAGE_NAME) TAG=$(TAG) docker-compose build

# Push Docker images to Docker Hub
.PHONY: push
push:
	IMAGE_NAME=$(IMAGE_NAME) TAG=$(TAG) docker-compose push

# Deploy to Kubernetes (production)
.PHONY: deploy-prod
deploy-prod:
	kubectl apply -f kubernetes/prod/app-prod-deployment-flask.yml
	kubectl apply -f kubernetes/prod/app-prod-deployment-redis.yml
	kubectl apply -f kubernetes/prod/app-prod-deployment-worker.yml
	kubectl apply -f kubernetes/prod/app-prod-ingress-flask.yml
	kubectl apply -f kubernetes/prod/app-prod-service-flask.yml
	kubectl apply -f kubernetes/prod/app-prod-service-redis.yml
	kubectl apply -f kubernetes/prod/app-prod-service-nodeport-flask.yml

# Deploy to Kubernetes (test environment)
.PHONY: deploy-test
deploy-test:
	kubectl apply -f kubernetes/test/app-test-deployment-flask.yml
	kubectl apply -f kubernetes/test/app-test-deployment-redis.yml
	kubectl apply -f kubernetes/test/app-test-deployment-worker.yml
	kubectl apply -f kubernetes/test/app-test-ingress-flask.yml
	kubectl apply -f kubernetes/test/app-test-service-flask.yml
	kubectl apply -f kubernetes/test/app-test-service-redis.yml
	kubectl apply -f kubernetes/test/app-test-service-nodeport-flask.yml

# Run the Flask API locally (docker-compose)
.PHONY: run-local
run-local:
	docker-compose up flask-app

# Run the worker locally (docker-compose)
.PHONY: run-worker
run-worker:
	docker-compose up worker

# Run tests using pytest
.PHONY: test
test:
	pytest test/

# Clean up local Docker containers and images
.PHONY: clean
clean:
	docker-compose down
	docker rmi $(IMAGE_NAME):$(TAG)

# View logs for Flask app
.PHONY: logs-flask
logs-flask:
	kubectl logs -f $(CONTAINER_NAME)

# View logs for Worker
.PHONY: logs-worker
logs-worker:
	kubectl logs -f $(WORKER_NAME)

# View logs for Redis
.PHONY: logs-redis
logs-redis:
	kubectl logs -f $(REDIS_SERVICE)


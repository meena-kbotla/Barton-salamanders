IMAGE_NAME = salamander-api
TAG = latest

# Build all containers
.PHONY: build
build:
	docker-compose build

# Start containers
.PHONY: up
up:
	docker-compose up --build

# Stop containers
.PHONY: down
down:
	docker-compose down

# Run only the Flask app
.PHONY: run-local
run-local:
	docker-compose up flask-app

# Run only the worker
.PHONY: run-worker
run-worker:
	docker-compose up worker

# Push image to Docker Hub (must docker login first)
.PHONY: push
push:
	docker tag $(IMAGE_NAME):$(TAG) your_dockerhub_username/$(IMAGE_NAME):$(TAG)
	docker push your_dockerhub_username/$(IMAGE_NAME):$(TAG)

# View logs
.PHONY: logs
logs:
	docker-compose logs -f

# Run tests
.PHONY: test
test:
	pytest test/


.PHONY: install test lint run generate-sample-day docker-run

install:
	pip install -e ".[dev]" 2>/dev/null || pip install -r requirements-dev.txt && pip install -e .

test:
	pytest -v --cov=analytics_pipeline --cov-report=term-missing

lint:
	flake8 src tests
	black --check src tests

run:
	python -m analytics_pipeline.cli run

generate-sample-day:
	python scripts/generate_sample_events.py --date 2023-10-27 --events 40

docker-run:
	docker compose up --build pipeline

.PHONY: install api test lint eval seed demo lint

install:
	python -m pip install -e ".[dev]"

api:
	uvicorn apps.api.main:app --reload --port 8000

test:
	pytest -q

lint:
	ruff check .

eval:
	python -m evals.runners.rag_eval
	python -m evals.runners.decision_eval

seed:
	python -m scripts.seed_dev_set


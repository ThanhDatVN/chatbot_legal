PY ?= .venv/Scripts/python.exe
SNAPSHOT ?= corpus-2026-10-01

.PHONY: setup sources ingest index index-docker run-api run-ui up test security-test eval screenshots

setup:            ## install dependencies into .venv (CUDA or CPU torch must be installed separately)
	$(PY) -m pip install -r requirements/dev.txt

sources:          ## download official PDFs listed in the registry and verify SHA-256
	$(PY) scripts/download_sources.py

ingest:           ## build the corpus snapshot; fails if any quality gate fails
	$(PY) -X utf8 -m ingestion.build --snapshot-id $(SNAPSHOT)

index:            ## embed chunks (cached) and build Qdrant + BM25 indexes locally
	$(PY) -X utf8 -m app.indexing

index-docker:     ## same, into the Qdrant container (reuses the embedding cache)
	docker compose up -d qdrant
	docker compose run --rm api python -m app.indexing

run-api:
	$(PY) -X utf8 -m uvicorn app.api.main:app --port 8000

run-ui:
	API_URL=http://127.0.0.1:8000 $(PY) -m streamlit run ui/app.py

up:
	docker compose up --build

test:             ## unit, integration and security tests
	$(PY) -m pytest tests

security-test:
	$(PY) -m pytest tests/security && $(PY) -X utf8 -m evaluation.security_eval

eval:             ## retrieval benchmark, threshold tuning (dev) and A-D answer benchmark (test)
	$(PY) -X utf8 -m evaluation.dataset_v2
	$(PY) -X utf8 -m evaluation.retrieval_eval --split all
	$(PY) -X utf8 -m evaluation.tune_policy
	$(PY) -X utf8 -m evaluation.answer_eval --split test
	$(PY) -X utf8 -m evaluation.report

screenshots:      ## needs the API and UI running
	node scripts/screenshot.mjs assets/screenshots

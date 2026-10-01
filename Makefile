PY := .venv/bin/python
export PYTHONPATH := src/backend

.PHONY: setup seed api web test evals tokens lint e2e load up down

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r src/backend/requirements.txt
	cd src/frontend && npm install

seed:
	$(PY) scripts/seed.py

api:
	.venv/bin/uvicorn raw.main:app --reload --port 8000

web:
	cd src/frontend && npm run dev

test:
	LLM_MODE=offline .venv/bin/pytest tests/unit tests/api -q

lint:
	.venv/bin/ruff check src/backend tests evals scripts

evals:
	LLM_MODE=$${LLM_MODE:-replay} $(PY) evals/run_evals.py

tokens:
	$(PY) ops/token_report.py

e2e:
	cd src/frontend && npx playwright test

load:
	k6 run tests/load/smoke.js

up:
	docker compose -f ops/deploy/docker-compose.yml up -d --build

down:
	docker compose -f ops/deploy/docker-compose.yml down

PY := .venv/bin/python
export PYTHONPATH := src/backend

.PHONY: setup seed reseed api web test evals evals-live tokens lint e2e load up down

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r src/backend/requirements.txt
	cd src/frontend && npm install

seed:
	$(PY) scripts/seed.py

reseed:
	$(PY) scripts/seed.py --reset

api:
	.venv/bin/uvicorn raw.main:app --reload --port 8000

web:
	cd src/frontend && npm run dev

test:
	LLM_MODE=offline .venv/bin/pytest tests/unit tests/api -q

lint:
	.venv/bin/ruff check src/backend tests evals scripts ops
	cd src/frontend && npm run typecheck

evals:
	$(PY) evals/run_evals.py --mode $${LLM_MODE:-replay}
	$(PY) evals/run_evals.py --mode $${LLM_MODE:-replay} --dataset data/synthetic/change_requests.jsonl --label heldout

evals-live:  # needs free GEMINI_API_KEY / GROQ_API_KEY; records responses so CI can replay them
	$(PY) evals/run_evals.py --mode live --record --label live

tokens:
	mkdir -p evals/.work && rm -f evals/.work/tokens.db
	$(PY) evals/run_evals.py --mode $${LLM_MODE:-offline} --keep-db evals/.work/tokens.db --consistency 0 --no-gate --label tokens
	rm -f evals/results/*-tokens.md evals/results/*-tokens.json
	$(PY) ops/token_report.py --db evals/.work/tokens.db

e2e:
	cd src/frontend && npx playwright test

load:
	@command -v k6 >/dev/null && k6 run tests/load/smoke.js || \
	  docker run --rm -i -e BASE=http://host.docker.internal:8000 grafana/k6 run - < tests/load/smoke.js

up:
	docker compose -f ops/deploy/docker-compose.yml up -d --build

down:
	docker compose -f ops/deploy/docker-compose.yml down

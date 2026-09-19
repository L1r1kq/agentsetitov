.PHONY: install test eval-llm eval-agent serve compose-core compose-obs

install:
	python3 -m pip install -e ".[dev]"

test:
	python3 -m pytest -q

eval-llm:
	python3 -m agentse eval-llm

eval-agent:
	python3 -m agentse eval-agent

serve:
	python3 -m agentse serve

compose-core:
	docker compose -f deploy/docker-compose.yml --profile core up --build

compose-obs:
	docker compose -f deploy/docker-compose.yml --profile obs up

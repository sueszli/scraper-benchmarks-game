.PHONY: venv
venv:
	uv sync
	@echo "\nActivate with: source .venv/bin/activate"

.PHONY: fmt
fmt:
	uvx isort .
	uvx autoflake --remove-all-unused-imports --recursive --in-place .
	uvx black --line-length 5000 .
	uvx ruff check --fix --ignore F403,F405,F821,E731,E402 .

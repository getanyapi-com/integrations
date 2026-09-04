help:	## Show all Makefile targets.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'

format:	## Run the code autoformatter (ruff).
	ruff format .
	ruff check --fix .

lint:	## Run linters: ruff and mypy --strict.
	ruff check .
	ruff format --check .
	mypy

test:	## Run tests via pytest.
	pytest tests

gate:	## Run the full release gate.
	ruff check . && ruff format --check . && mypy && pytest

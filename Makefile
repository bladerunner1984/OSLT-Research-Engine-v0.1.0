.PHONY: install test unit integration preflight api schemas package

install:
	python -m pip install -e ".[dev]"

unit:
	pytest tests/unit

integration:
	pytest tests/integration

test:
	pytest --cov=oslt_research --cov-report=term-missing --cov-fail-under=80

preflight:
	python scripts/preflight.py

schemas:
	python scripts/export_schemas.py

api:
	uvicorn oslt_research.api.app:app --reload

package:
	rm -rf dist build *.egg-info src/*.egg-info
	python -m pip wheel . --no-deps --no-build-isolation -w dist

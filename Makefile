.PHONY: help build backend core integrations fmt test clean

help:
	@echo "Targets:"
	@echo "  build         Build all three projects"
	@echo "  backend       sbt compile"
	@echo "  core          cargo build --release"
	@echo "  integrations  pip install -e integrations[dev]"
	@echo "  fmt           Format all languages"
	@echo "  test          Run all test suites"
	@echo "  clean         Remove build artefacts"

build: backend core integrations

backend:
	cd backend && sbt compile

core:
	cd core && cargo build --release

integrations:
	cd integrations && pip install -e ".[dev]"

fmt:
	cd backend && sbt scalafmtAll
	cd core && cargo fmt
	cd integrations && ruff format src tests

test:
	cd backend && sbt test
	cd core && cargo test
	cd integrations && pytest

clean:
	cd backend && sbt clean
	cd core && cargo clean
	rm -rf integrations/.pytest_cache integrations/**/__pycache__

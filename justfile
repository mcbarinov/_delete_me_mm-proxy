set dotenv-load
project_name := `grep APP_NAME .env | cut -d '=' -f 2-`
version := `uv run python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])'`
docker_registry := `grep DOCKER_REGISTRY .env | cut -d '=' -f2`
docker_build_platform := env_var_or_default("DOCKER_BUILD_PLATFORM", "linux/amd64")
project_image := docker_registry+"/"+project_name

default: dev

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist src/*.egg-info

sync:
    uv sync

build: clean lint audit test
    uv build --wheel

format:
    uv run ruff check --select I --fix src tests
    uv run ruff format src tests

lint: format
    uv run ruff check src tests
    uv run mypy src

audit:
    uv run pip-audit
    uv run bandit -r -c "pyproject.toml" src

test:
    uv run pytest tests

docker-lint:
    hadolint docker/Dockerfile

docker-build:
	docker build --platform {{docker_build_platform}} -t {{project_name}}:{{version}} --file docker/Dockerfile .
	docker tag {{project_name}}:{{version}} {{project_name}}:latest

docker-compose: docker-build
	cd docker && docker compose up --build

docker-upload: docker-build
    git diff-index --quiet HEAD
    docker tag {{project_name}}:{{version}} {{project_image}}:{{version}}
    docker push {{project_image}}:{{version}}

publish: docker-upload
	cd ansible;	ansible-playbook -i hosts.yml --extra-vars="app_version={{version}}" -t publish playbook.yml
	git tag -a 'v{{version}}' -m 'v{{version}}' && git push origin v{{version}}

dev:
	uv run uvicorn --reload --port 3000 --log-level warning app.main:server

gunicorn:
	uv run gunicorn -b 0.0.0.0:3000 --timeout 999 --threads 12 -k uvicorn.workers.UvicornWorker app.main:server

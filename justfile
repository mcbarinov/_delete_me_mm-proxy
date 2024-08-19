set dotenv-load
project_name := `grep APP_NAME .env | cut -d '=' -f 2-`
version := `python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])'`
docker_registry := `grep DOCKER_REGISTRY .env | cut -d '=' -f2`
project_image := docker_registry+"/"+project_name

default: dev

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info

pip-compile:
    rm -f requirements.txt requirements-dev.txt
    uv pip compile --refresh -o requirements.txt pyproject.toml
    uv pip compile --refresh -o requirements-dev.txt --extra=dev pyproject.toml

pip-sync:
    uv pip sync requirements-dev.txt
    uv pip install -e .

pip-upgrade: pip-compile pip-sync
    echo done

build: clean lint audit test
    python -m build

format:
    ruff check --select I --fix src tests
    ruff format src tests

lint: format
    ruff check src tests
    mypy src

audit:
    pip-audit
    bandit -r -c "pyproject.toml" src

test:
    pytest tests

docker-lint:
    hadolint --ignore DL3008 docker/Dockerfile

docker-build: build docker-lint
	docker build --platform linux/amd64 -t {{project_name}}:{{version}} --file docker/Dockerfile .
	docker tag {{project_name}}:{{version}} {{project_name}}:latest

docker-compose: docker-build
	cd docker && docker compose up --build

docker-upload: docker-build
	docker tag {{project_name}}:{{version}} {{project_image}}:{{version}}
	docker push {{project_image}}:{{version}}

publish: docker-upload
	cd ansible;	ansible-playbook -i hosts.yml --extra-vars="app_version={{version}}" -t publish playbook.yml

dev:
	uvicorn --reload --port 3000 --log-level warning app.main:server

gunicorn:
	gunicorn -b 0.0.0.0:3000 --timeout 999 --threads 12 -k uvicorn.workers.UvicornWorker app.main:server

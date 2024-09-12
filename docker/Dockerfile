# syntax=docker/dockerfile:1.9
FROM python:3.12.6 AS builder

SHELL ["/bin/sh", "-exc"]
WORKDIR /project

# Setup uv
COPY --from=ghcr.io/astral-sh/uv:0.4.9 /uv /usr/local/bin/
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.12 \
    UV_PROJECT_ENVIRONMENT=/app

# Create a virtual environment
RUN --mount=type=cache,target=/root/.cache uv venv $UV_PROJECT_ENVIRONMENT

# Install dependencies
COPY pyproject.toml uv.lock /project/
RUN --mount=type=cache,target=/root/.cache uv sync --frozen --no-install-project --no-dev

# Build the project
COPY src/ /project/
RUN --mount=type=cache,target=/root/.cache/uv uv build --wheel -o /dist /project

# Install the project package
RUN --mount=type=cache,target=/root/.cache uv pip install --python=$UV_PROJECT_ENVIRONMENT --no-deps /dist/*.whl


FROM python:3.12.6-slim
ENV PATH="/app/bin:$PATH"

RUN <<EOT
groupadd -r app
useradd -r -d /app -g app -N app
mkdir /data
chown -R app:app /data
EOT

COPY --from=builder --chown=app:app /app /app

USER app
WORKDIR /app
EXPOSE 3000
CMD ["gunicorn", "-b", "0.0.0.0:3000", "--timeout", "999", "--threads", "24", "-k", "uvicorn.workers.UvicornWorker", "app.main:server"]

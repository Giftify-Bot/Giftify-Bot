# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

FROM python:3.11-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install poetry for installing dependencies.
RUN python -m pip install poetry

# Copy the project files.
COPY poetry.lock pyproject.toml /app/

# Install the project dependencies using poetry.
RUN poetry install -n --no-dev --no-root -E uvloop

# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 8080

# Run the application.
ENTRYPOINT poetry run python -O .
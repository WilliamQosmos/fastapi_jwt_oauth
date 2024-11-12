FROM python:3.11-alpine AS requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --without dev

FROM python:3.11-alpine AS production-stage

ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app/

EXPOSE 8000

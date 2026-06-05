FROM python:3.12-slim

RUN groupadd --gid 1001 app && useradd --uid 1001 --gid 1001 --no-create-home app

WORKDIR /app

COPY pyproject.toml .
COPY . .
RUN pip install --no-cache-dir -e ".[dev]" && chown -R app:app /app

USER app

CMD ["uvicorn", "soulra.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Build from the repository root:
#   docker build -f enterprise/Dockerfile -t veritas-enterprise .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY enterprise ./enterprise

RUN useradd --system --uid 10002 veritas && chown -R veritas /app
USER veritas

EXPOSE 8100

CMD ["sh", "-c", "alembic -c enterprise/alembic.ini upgrade head && uvicorn enterprise.main:app --host 0.0.0.0 --port 8100"]

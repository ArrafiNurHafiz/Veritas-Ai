FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VERITAS_DB=/data/veritas.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY veritas_harness.py llm_planner.py agent_service.py anchor_chain.py seed_demo.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

RUN useradd --system --uid 10001 veritas && mkdir -p /data && chown veritas /data
USER veritas

EXPOSE 8002
ENTRYPOINT ["./entrypoint.sh"]

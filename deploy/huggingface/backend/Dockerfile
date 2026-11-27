FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent_service.py llm_planner.py anchor_chain.py ./
COPY enterprise ./enterprise
COPY erp_sandbox ./erp_sandbox
COPY mail_sandbox ./mail_sandbox
COPY deploy/huggingface/backend/start.sh ./start.sh
RUN chmod +x ./start.sh

RUN useradd -m -u 1000 user && mkdir -p /data && chown -R user:user /app /data
USER user

EXPOSE 7860
CMD ["./start.sh"]

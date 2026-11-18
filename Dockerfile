FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir psutil>=5.9.0 requests>=2.31.0

COPY agent.py .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

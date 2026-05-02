FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only torch first (avoids ~700MB CUDA wheel on VPS without GPU)
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "testing.realtime_testing", "--symbol", "LINK/USDT", "--model", "cnn_bilstm_am", "--rrr", "2.0", "--capital", "1000", "--timeframe", "1h", "--threshold", "0.015", "--sizing-mode", "dynamic"]

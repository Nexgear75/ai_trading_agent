FROM python:3.10-slim

WORKDIR /app

# Installation des dépendances système pour compiler certains packages si nécessaire
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'intégralité du projet
COPY . .

# Configuration de l'environnement
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Commande par défaut (sera surchargée par le docker-compose)
CMD ["python", "-m", "testing.realtime_testing", "--symbol", "LINK/USDT", "--model", "cnn_bilstm_am", "--rrr", "2.0", "--capital", "1000", "--timeframe", "1h", "--threshold", "0.015", "--fresh", "--sizing-mode", "dynamic"]

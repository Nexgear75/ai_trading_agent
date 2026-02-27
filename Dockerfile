# ============================================================================
# AI Trading Pipeline — Dockerfile (MVP)
# Référence : docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md §16
# ============================================================================

FROM python:3.11-slim

# Prevent Python buffering (logs en temps réel)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dépendances système (si besoin de compilation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source et la config
COPY configs/ configs/
COPY docs/ docs/
COPY . .

# Point d'entrée par défaut (à adapter quand le pipeline sera implémenté)
# Exemple : python -m stockgpt.run --config configs/default.yaml
CMD ["python", "--version"]

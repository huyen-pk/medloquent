FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system deps required for audio processing and building native wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
    espeak-ng \
       git \
       wget \
       ffmpeg \
       libsndfile1 \
       libsndfile1-dev \
       libasound2-dev \
       libportaudio2 \
       libssl-dev \
       libffi-dev \
       libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer cache
COPY synthetic/requirements-full.txt /app/requirements-full.txt

# Upgrade pip and install Python deps (may be large)
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir -r /app/requirements-full.txt

# Copy pipeline source
COPY synthetic /app/synthetic

# Create an unprivileged user and switch to it
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

ENV HF_HOME=/home/appuser/.cache/huggingface

WORKDIR /app/synthetic

CMD ["python", "-m", "synthetic.cli", "run-all"]

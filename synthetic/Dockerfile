FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    wget \
    unzip \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# copy only requirements first for caching
COPY requirements.txt /workspace/requirements.txt

RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# copy entire repo into the container workspace
COPY . /workspace

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /workspace

CMD ["python", "-m", "synthetic.cli", "--help"]

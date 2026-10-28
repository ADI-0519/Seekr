FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
  build-essential \
  libpq-dev \
  ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
  pip install -r requirements.txt

ARG INSTALL_ML=false
COPY requirements_ml.txt ./requirements_ml.txt
RUN --mount=type=cache,target=/root/.cache/pip \
  if [ "$INSTALL_ML" = "true" ]; then \
    pip install --index-url https://download.pytorch.org/whl/cpu \
      torch==2.1.2+cpu torchvision==0.16.2+cpu \
    && pip install -r requirements_ml.txt; \
  fi

COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic


RUN useradd --create-home --shell /bin/bash celeryuser \
  && mkdir -p /home/celeryuser/.cache/huggingface/hub \
  && mkdir -p /home/celeryuser/.EasyOCR/model \
  && chown -R celeryuser:celeryuser /home/celeryuser/.cache /home/celeryuser/.EasyOCR
USER celeryuser


CMD ["python","-m","uvicorn","app.main:app", "--host=0.0.0.0","--port","8000"]

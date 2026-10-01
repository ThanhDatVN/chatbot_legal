# API service: FastAPI + retrieval models on CPU
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/root/.cache/huggingface MODEL_DEVICE=cpu
WORKDIR /app
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0
COPY requirements/api.txt requirements/api.txt
RUN pip install -r requirements/api.txt
COPY pyproject.toml ./
COPY app app
COPY ingestion ingestion
COPY evaluation evaluation
COPY scripts scripts
COPY data/corpus data/corpus
COPY data/eval data/eval
COPY data/review data/review
COPY reports reports
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=240s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/src PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# Train a model at build time so the image ships ready-to-serve.
RUN python -m credit_risk.train 20000
EXPOSE 8000 8501
CMD ["uvicorn", "credit_risk.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]

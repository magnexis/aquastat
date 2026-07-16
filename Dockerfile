FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY app /app/app
COPY scripts /app/scripts
COPY sql /app/sql
COPY prometheus.yml /app/prometheus.yml

RUN python -m pip install --upgrade pip && \
    python -m pip install --prefix=/install .

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PROMETHEUS_MULTIPROC_DIR=/tmp

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /install /usr/local
COPY app /app/app
COPY scripts /app/scripts
COPY sql /app/sql
COPY README.md pyproject.toml render.yaml prometheus.yml /app/

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

# Image of the benchmark service (ADR-0001): the HTTP API that starts runs against Ollama
# and delivers the result to the NFHotel web API. The notebook and its libraries are not
# installed (extra "notebook"). Build context is the repository root:
#   docker build -t benchmark:local .
# Settings come from the environment (deploy/benchmark.env.example); no secret is in the image.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# The dependencies come from requirements.lock: every version is pinned with its hashes and only
# wheels are installed, so no setup script of a package runs at build time. Regenerate it with
#   pip-compile --generate-hashes --strip-extras --allow-unsafe --output-file=requirements.lock pyproject.toml
# in a python:3.13-slim container. The service itself is not installed; its source is on PYTHONPATH.
WORKDIR /app
COPY requirements.lock ./
RUN pip install --only-binary :all: --require-hashes --no-deps -r requirements.lock
COPY src ./src
ENV PYTHONPATH=/app/src

# The synthetic example dataset; mount a real dataset and set NFBENCH_DATASET to use it.
COPY data/example ./data/example

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown app /data
USER app

ENV NFBENCH_DATA_DIR=/data \
    NFBENCH_DATASET=/app/data/example/synthetic_hotel_bookings.csv
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "--factory", "nfbench.bootstrap:create_service_app", "--host", "0.0.0.0", "--port", "8000"]

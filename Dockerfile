FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 campus \
    && useradd --uid 10001 --gid campus --no-create-home campus

COPY app/ ./app/
COPY migrations/ ./migrations/
COPY tests/ ./tests/
COPY config.py run.py ./
COPY scripts/start_web.py ./scripts/start_web.py
USER 10001:10001
EXPOSE 8000
CMD ["python", "scripts/start_web.py"]

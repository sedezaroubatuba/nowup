FROM postgres:18-bookworm AS pgtools
FROM python:3.12-slim-bookworm
WORKDIR /app
# Native clients are used for consistent PostgreSQL backups and restores.
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 liblz4-1 libzstd1 && rm -rf /var/lib/apt/lists/*
COPY --from=pgtools /usr/lib/postgresql/18/bin/pg_dump /usr/local/bin/pg_dump
COPY --from=pgtools /usr/lib/postgresql/18/bin/pg_restore /usr/local/bin/pg_restore
COPY --from=pgtools /usr/lib/x86_64-linux-gnu/libpq.so.5* /usr/lib/x86_64-linux-gnu/
RUN ldconfig && pg_dump --version && pg_restore --version
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV NOWUP_HTTPS=1
EXPOSE 8000
CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]

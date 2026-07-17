FROM python:3.11-slim

WORKDIR /app

# Build tools needed by a few packages that ship without prebuilt wheels for
# every platform (e.g. the `jq` binding wraps libjq/oniguruma in C).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        pkg-config \
        autoconf \
        automake \
        libtool \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Single worker: the rate limiter and login-lockout guard keep state in
# process memory, so multiple uvicorn workers would each enforce limits
# independently. Scale horizontally with more containers behind the proxy
# instead, or move that state to Mongo/Redis first if you need >1 worker here.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

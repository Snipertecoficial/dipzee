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

# Stamp the image with the git commit so /api/health reports exactly which
# revision is live. CI passes --build-arg GIT_SHA=${{ github.sha }}; defaults
# to "dev" for local builds. Placed after COPY so it never busts the pip layer.
ARG GIT_SHA=dev
ENV GIT_SHA=$GIT_SHA

EXPOSE 8000

# Single worker: the rate limiter and login-lockout guard keep state in
# process memory, so multiple uvicorn workers would each enforce limits
# independently. Scale horizontally with more containers behind the proxy
# instead, or move that state to Mongo/Redis first if you need >1 worker here.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

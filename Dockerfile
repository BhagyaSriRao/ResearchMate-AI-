FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend files
COPY . .

# Expose standard port (overridden by $PORT at runtime)
EXPOSE 8000

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:${PORT:-8000}/api/status || exit 1

# Start FastAPI backend
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

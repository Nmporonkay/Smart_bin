FROM python:3.11-slim

# Install system dependencies for GPIO access before running pip
RUN apt-get update && apt-get install -y \
    python3-lgpio \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pirlib/ ./pirlib/
COPY producer.py .

CMD ["python", "producer.py"]
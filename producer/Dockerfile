FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pirlib/ ./pirlib/
COPY producer.py .

# Default: mock mode (no real GPIO). Override with MOCK=false on real hardware.
ENV MOCK=true

CMD ["python", "producer.py"]

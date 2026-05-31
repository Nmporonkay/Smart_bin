FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p models

COPY api/api.py .

EXPOSE 5000

CMD ["python", "api.py"]

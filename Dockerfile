FROM python:3.11-slim
WORKDIR /home/iotlab_upat_3/labs/Smart_bin
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pirlib ./pirlib
COPY producer.py .
COPY consumer.py .
CMD python run_pipeline.py \
    --device-id pir-01 \
    --pin 17 \
    --sample-interval 0.1 \
    --cooldown-s 2 \
    --min-high-s 0.5 \
    --queue-size 100 \
    --consumer-delay 0.0 \
    --duration 60 \
    --out motion_pipeline.jsonl \
    --verbose
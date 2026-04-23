FROM python:3.11-slim
WORKDIR /home/iotlab_upat_3/labs/Smart_bin
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pirlib ./pirlib
COPY producer.py .
COPY consumer.py .
CMD python consumer.py \
    --broker localhost \
    --topic "smartbin/bin-01/pir-01/events" \
    --out output/events.jsonl \
    --verbose \
    python producer.py \
    --broker localhost \
    --topic smartbin/bin-01/pir-01/events \
    --pin 17 \
    --verbose
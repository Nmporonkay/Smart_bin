# Smart Bin — Lab 06 (Dockerized)

## Repository Structure

```
lab06/
├── docker-compose.yml
├── requirements.txt
├── producer.py
├── consumer.py
├── mosquitto/
│   └── mosquitto.conf
├── producer/
│   └── Dockerfile
├── consumer/
│   └── Dockerfile
└── pirlib/
    ├── __init__.py
    ├── sampler.py       ← supports mock mode for non-Pi environments
    └── interpreter.py
```

---

## Running with Docker (recommended)

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/) (included in Docker Desktop)

### Start everything

```bash
docker compose up --build
```

This starts 3 services: **broker** (Mosquitto), **producer**, and **consumer**.

The producer runs in **mock mode** by default — it simulates PIR sensor events
without needing real GPIO hardware. To stop:

```bash
docker compose down
```

### View consumer output (events JSONL)

```bash
docker exec smartbin-consumer cat output/events.jsonl
```

Or follow it live:

```bash
docker exec smartbin-consumer tail -f output/events.jsonl
```

### Run on real Raspberry Pi hardware

1. In `docker-compose.yml`, uncomment under the `producer` service:
   ```yaml
   privileged: true
   devices:
     - /dev/gpiomem:/dev/gpiomem
   ```
2. Change the `MOCK` environment variable to `"false"`:
   ```yaml
   MOCK: "false"
   ```
3. Run `docker compose up --build`

---

## Running without Docker (manual)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Install and start Mosquitto broker

```bash
sudo apt-get install -y mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

### Step 1 — Start the consumer

```bash
python consumer.py \
  --broker localhost \
  --port 1883 \
  --topic "smartbin/bin-01/pir-01/events" \
  --out events.jsonl \
  --qos 1 \
  --verbose
```

### Step 2 — Start the producer

```bash
python producer.py \
  --broker localhost \
  --port 1883 \
  --topic "smartbin/bin-01/pir-01/events" \
  --pin 17 \
  --cooldown 2.0 \
  --min-high 0.1 \
  --sample-interval 0.1 \
  --qos 1 \
  --verbose
```

---

## Changes in this version

| File | Change |
|---|---|
| `sampler.py` | Added mock mode — simulates PIR events when `MOCK=true` |
| `producer.py` | JSON-LD `@context` moved to module-level constant; reads config from env vars |
| `consumer.py` | Output file kept open for lifetime of process (not re-opened per message); reads config from env vars |
| `requirements.txt` | Versions pinned for reproducible Docker builds |
| `docker-compose.yml` | New — orchestrates broker + producer + consumer |
| `mosquitto/mosquitto.conf` | New — broker configuration |
| `producer/Dockerfile` | New |
| `consumer/Dockerfile` | New |

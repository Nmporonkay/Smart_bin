import argparse
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from queue import Empty, Full, Queue

from pirlib.interpreter import PirInterpreter
from pirlib.sampler import PirSampler

def parse_iso_utc(s: str):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def producer(stop_flag, sampler, interpreter, out_queue, sample_interval,
             device_id, metrics, metrics_lock):
    run_id = str(uuid.uuid4())
    seq = 0

    while not stop_flag.is_set():
        current_time = time.time()
        sample = sampler.read()
        events = interpreter.update(sample, current_time)

        for _event in events:
            seq += 1
            record = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "device_id": device_id,
                "event_type": "motion",
                "motion_state": "detected",
                "sequence_number": seq,
                "run_id": run_id,
            }

            try:
                out_queue.put_nowait(record)
                with metrics_lock:
                    metrics["produced"] += 1
            except Full:
                with metrics_lock:
                    metrics["dropped"] += 1

        time.sleep(sample_interval)

def consumer(stop_flag, in_queue, output_path, metrics, metrics_lock, consumer_delay=0.0):
    with open(output_path, "a", encoding="utf-8") as f:
        while not stop_flag.is_set() or not in_queue.empty():
            try:
                record = in_queue.get(timeout=0.5)
            except Empty:
                continue

            try:
                ingest_time = datetime.now(timezone.utc).isoformat()
                record["ingest_time_utc"] = ingest_time

                event_time = parse_iso_utc(record["timestamp_utc"])
                ingest_dt = parse_iso_utc(ingest_time)
                latency_ms = (ingest_dt - event_time).total_seconds() * 1000.0
                record["pipeline_latency_ms"] = round(latency_ms, 3)

                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()

                with metrics_lock:
                    metrics["consumed"] += 1
                    metrics["max_queue"] = max(metrics["max_queue"], in_queue.qsize())
            finally:
                in_queue.task_done()

            if consumer_delay:
                time.sleep(consumer_delay)

def main():
    # 1. Setup Argument Parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", type=int, default=22)
    parser.add_argument("--out", type=str, default="events.jsonl")
    parser.add_argument("--queue-size", type=int, default=100)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--sample-interval", type=float, default=0.1)
    parser.add_argument("--cooldown-s", type=float, default=2.0)
    parser.add_argument("--min-high-s", type=float, default=0.1)
    parser.add_argument("--device-id", type=str, default="pi-01")
    parser.add_argument("--consumer-delay", type=float, default=0.0)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # 2. Initialize Shared Objects
    event_q = Queue(maxsize=args.queue_size)
    metrics = {"produced": 0, "consumed": 0, "dropped": 0, "max_queue": 0}
    metrics_lock = threading.Lock()
    stop_flag = threading.Event()

    sampler = PirSampler(args.pin)
    interpreter = PirInterpreter(cooldown_s=args.cooldown_s, min_high_s=args.min_high_s)

    # 3. Setup Threads
    producer_thread = threading.Thread(
        target=producer,
        args=(stop_flag, sampler, interpreter, event_q, args.sample_interval, args.device_id, metrics, metrics_lock),
        daemon=True
    )

    consumer_thread = threading.Thread(
        target=consumer,
        args=(stop_flag, event_q, args.out, metrics, metrics_lock, args.consumer_delay),
        daemon=True
    )

    producer_thread.start()
    consumer_thread.start()

    # 4. Monitor Loop
    start_time = time.time()
    try:
        while time.time() - start_time < args.duration:
            if args.verbose:
                with metrics_lock:
                    print(f"[status] p={metrics['produced']} c={metrics['consumed']} d={metrics['dropped']} q={event_q.qsize()}")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stop_flag.set()
        producer_thread.join(timeout=2)
        consumer_thread.join(timeout=2)
        print(f"\nFinal Results: {metrics}")

if __name__ == "__main__":
    main()
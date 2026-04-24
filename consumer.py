import argparse
import os
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def parse_args():
    parser = argparse.ArgumentParser(description="PIR Motion Event Consumer")
    parser.add_argument("--broker",  type=str, default=os.environ.get("MQTT_BROKER", "localhost"))
    parser.add_argument("--port",    type=int, default=int(os.environ.get("MQTT_PORT", 1883)))
    parser.add_argument("--topic",   type=str, default=os.environ.get("MQTT_TOPIC", "smartbin/bin-01/pir-01/events"))
    parser.add_argument("--qos",     type=int, default=int(os.environ.get("QOS", 1)), choices=[0, 1, 2])
    parser.add_argument("--out",     type=str, default=os.environ.get("OUT_FILE", "output/events.jsonl"))
    parser.add_argument("--verbose", action="store_true", default=os.environ.get("VERBOSE", "").lower() == "true")
    return parser.parse_args()


def make_on_message(output_file, verbose, metrics):
    """
    Returns the MQTT on_message callback.
    output_file is an already-open file handle (kept open for the lifetime
    of the consumer, avoiding repeated open/close on every message).
    """
    def on_message(client, userdata, msg):
        try:
            payload_str = msg.payload.decode("utf-8")
            record = json.loads(payload_str)

            ingest_time = datetime.now(timezone.utc)
            record["ingest_time_utc"] = ingest_time.isoformat()

            if "timestamp_utc" in record:
                event_time = datetime.fromisoformat(record["timestamp_utc"])
                latency_ms = (ingest_time - event_time).total_seconds() * 1000.0
                record["pipeline_latency_ms"] = round(latency_ms, 3)

                metrics["total_received"] += 1
                metrics["total_latency_ms"] += latency_ms
                avg_latency = metrics["total_latency_ms"] / metrics["total_received"]

                if verbose:
                    print(f"[consumer] MSG {metrics['total_received']} | "
                          f"seq: {record.get('sequence_number')} | "
                          f"latency: {latency_ms:.3f}ms | "
                          f"avg latency: {avg_latency:.3f}ms")
            else:
                print("[consumer] Warning: no timestamp_utc field in record.")

            # File handle stays open — no repeated open/close per message
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            output_file.flush()

        except json.JSONDecodeError:
            print("[consumer] Error: malformed JSON payload.")
        except Exception as e:
            print(f"[consumer] Error processing message: {e}")

    return on_message


def main():
    args = parse_args()

    # Ensure output directory exists (important inside Docker volumes)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    metrics = {"total_received": 0, "total_latency_ms": 0.0}

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    try:
        print(f"[consumer] Connecting to broker at {args.broker}:{args.port}...")
        client.connect(args.broker, args.port, 60)

        # Open the output file once and keep it open
        with open(args.out, "a", encoding="utf-8") as output_file:
            client.on_message = make_on_message(output_file, args.verbose, metrics)
            client.subscribe(args.topic, qos=args.qos)
            print(f"[consumer] Subscribed to '{args.topic}' with QoS {args.qos}.")
            print(f"[consumer] Writing output to: {args.out}")
            print("[consumer] Waiting for messages... (Ctrl+C to stop)")
            client.loop_forever()

    except KeyboardInterrupt:
        print("\n[consumer] Shutting down...")
        client.disconnect()
        print(f"[consumer] Final metrics: {metrics}")


if __name__ == "__main__":
    main()

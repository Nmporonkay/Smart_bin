import argparse
import time
import json
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from pirlib.sampler import PirSampler
from pirlib.interpreter import PirInterpreter


def parse_args():
    parser = argparse.ArgumentParser(description="PIR Motion Event Producer")
    parser.add_argument("--broker", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", type=str, default="smartbin/bin-01/pir-01/events")
    parser.add_argument("--status-topic", type=str, default="smartbin/bin-01/pir-01/status")
    parser.add_argument("--device-id", type=str, default="urn:dev:team03:pir-01")
    parser.add_argument("--pin", type=int, default=17)
    parser.add_argument("--sample-interval", type=float, default=0.1)
    parser.add_argument("--cooldown", type=float, default=2.0)
    parser.add_argument("--min-high", type=float, default=0.1)
    parser.add_argument("--qos", type=int, default=1, choices=[0, 1, 2])
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    # Initialize MQTT client
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    try:
        print(f"[producer] Connecting to broker at {args.broker}:{args.port}...")
        client.connect(args.broker, args.port, 60)
        client.loop_start()

        # Publish retained online status
        client.publish(args.status_topic, "online", retain=True, qos=args.qos)
        print(f"[producer] Status 'online' published to {args.status_topic}")

        # Initialize sampler and interpreter
        sampler = PirSampler(args.pin)
        interpreter = PirInterpreter(
            cooldown_s=args.cooldown,
            min_high_s=args.min_high
        )

        run_id = str(uuid.uuid4())
        seq = 0

        print(f"[producer] Started. Run ID: {run_id}. Publishing to: {args.topic}")

        while True:
            current_time = time.time()
            sample = sampler.read()
            events = interpreter.update(sample, current_time)

            for event in events:
                seq += 1

                record = {
                    "@context": {
                        "@vocab": "https://schema.org/",
                        "sosa": "http://www.w3.org/ns/sosa/",
                        "xsd": "http://www.w3.org/2001/XMLSchema#",
                        "pipeline": "https://github.com/Nmporonkay/Adv_Techs_Lab/blob/main/docs/ontology.md#",
                        "timestamp_utc": {
                            "@id": "sosa:resultTime",
                            "@type": "xsd:dateTime"
                        },
                        "device_id": {
                            "@id": "sosa:madeBySensor",
                            "@type": "@id"
                        },
                        "event_type": {
                            "@id": "sosa:observedProperty",
                            "@type": "xsd:string"
                        },
                        "motion_state": {
                            "@id": "pipeline:motionState",
                            "@type": "xsd:string"
                        },
                        "sequence_number": {
                            "@id": "pipeline:sequenceNumber",
                            "@type": "xsd:integer"
                        },
                        "run_id": {
                            "@id": "pipeline:runId",
                            "@type": "xsd:string"
                        },
                        "observedIn": {
                            "@id": "pipeline:observedIn",
                            "@type": "@id"
                        }
                    },
                    "@type": "sosa:Observation",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "device_id": args.device_id,
                    "event_type": "motion",
                    "motion_state": "detected",
                    "sequence_number": seq,
                    "run_id": run_id,
                    "observedIn": "urn:env:upatras:kypes-lab"
                }

                payload_str = json.dumps(record)
                client.publish(args.topic, payload_str, qos=args.qos)

                if args.verbose:
                    print(f"[producer] SEQ {seq} | event: {event['kind']} | "
                          f"high_for: {event['high_for_s']:.2f}s | "
                          f"topic: {args.topic}")

            time.sleep(args.sample_interval)

    except KeyboardInterrupt:
        print("\n[producer] Shutting down...")
    finally:
        client.publish(args.status_topic, "offline", retain=True, qos=args.qos)
        print(f"[producer] Status 'offline' published to {args.status_topic}")
        client.loop_stop()
        client.disconnect()
        print("[producer] Disconnected from broker.")


if __name__ == "__main__":
    main()
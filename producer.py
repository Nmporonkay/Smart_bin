import argparse
import time
import json
import uuid
from datetime import datetime, timezone
import os
import paho.mqtt.client as mqtt

from pirlib.sampler import PirSampler
from pirlib.interpreter import PirInterpreter


def parse_args():
    parser = argparse.ArgumentParser(description="PIR Motion Event Producer")
    parser.add_argument("--broker", type=str, default=os.environ.get("MQTT_BROKER", "localhost"))
    parser.add_argument("--port",   type=int, default=int(os.environ.get("MQTT_PORT", 1883)))
    parser.add_argument("--topic", type=str, default="smartbin/bin-01/pir-01/events")
    parser.add_argument("--status-topic", type=str, default="smartbin/bin-01/pir-01/status")
    parser.add_argument("--device-id", type=str, default="urn:dev:team03:pir-01")
    parser.add_argument("--bin-id", type=str, default="bin-01")
    parser.add_argument("--pin", type=int, default=17)
    parser.add_argument("--sample-interval", type=float, default=0.1)
    parser.add_argument("--cooldown", type=float, default=2.0)
    parser.add_argument("--min-high", type=float, default=0.1)
    parser.add_argument("--qos", type=int, default=1, choices=[0, 1, 2])
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def publish_ha_discovery(client, bin_id, device_id, qos):
    """Publish MQTT discovery configuration messages for Home Assistant."""
    # --- Motion sensor ---
    motion_unique_id = f"{bin_id}_pir_motion"
    motion_state_topic = f"smartbin/{bin_id}/pir-01/state"

    motion_config = {
        "name": f"SmartBin {bin_id} Motion",
        "state_topic": motion_state_topic,
        "payload_on": "detected",
        "payload_off": "clear",
        "device_class": "motion",
        "unique_id": motion_unique_id,
        "device": {
            "identifiers": [device_id],
            "name": f"SmartBin {bin_id}",
            "model": "PIR Motion Sensor",
            "manufacturer": "Team03",
        },
    }

    motion_discovery_topic = f"homeassistant/binary_sensor/{motion_unique_id}/config"
    client.publish(motion_discovery_topic, json.dumps(motion_config), retain=True, qos=qos)
    print(f"[producer] HA discovery published → {motion_discovery_topic}")

    # --- Motion event counter ---
    count_unique_id = "wastebin_01_motion_count"
    count_config = {
        "name": "Motion Event Count",
        "state_topic": f"smartbin/{bin_id}/pir-01/event_count",
        "unit_of_measurement": "events",
        "icon": "mdi:motion-sensor",
        "unique_id": count_unique_id,
        "device": {
            "identifiers": [bin_id],
            "name": "Smart Wastebin 01",
        },
    }

    count_discovery_topic = f"homeassistant/sensor/{count_unique_id}/config"
    client.publish(count_discovery_topic, json.dumps(count_config), retain=True, qos=qos)
    print(f"[producer] HA discovery published → {count_discovery_topic}")


def main():
    args = parse_args()

    ha_motion_state_topic = f"smartbin/{args.bin_id}/pir-01/state"
    ha_event_count_topic  = f"smartbin/{args.bin_id}/pir-01/event_count"

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    
    try:
        print(f"[producer] Connecting to broker at {args.broker}:{args.port}...")
        client.connect(args.broker, args.port, 60)
        client.loop_start()

        client.publish(args.status_topic, "online", retain=True, qos=args.qos)
        print(f"[producer] Status 'online' published to {args.status_topic}")

        publish_ha_discovery(client, args.bin_id, args.device_id, args.qos)

       
        client.publish(ha_motion_state_topic, "clear", qos=args.qos, retain=True)
        last_ha_state = "clear"
        
        
        sampler = PirSampler(args.pin)
        interpreter = PirInterpreter(
            cooldown_s=args.cooldown,
            min_high_s=args.min_high
        )
        run_id = str(uuid.uuid4())
        seq = 0

        print(f"[producer] Started. Run ID: {run_id}. Publishing to: {args.topic}")
        print("[producer] NOTE: events are logged by the consumer, not here.")

        last_ha_state = None

        while True:
            current_time = time.time()
            sample = sampler.read()
            events = interpreter.update(sample, current_time)

            if events:
                for event in events:
                    seq += 1

                    record = {
                        "@context": {
                            "@vocab": "https://schema.org/",
                            "sosa": "http://www.w3.org/ns/sosa/",
                            "xsd": "http://www.w3.org/2001/XMLSchema#",
                            "pipeline": "https://github.com/Nmporonkay/Adv_Techs_Lab/blob/main/docs/ontology.md#",
                            "timestamp_utc": {"@id": "sosa:resultTime", "@type": "xsd:dateTime"},
                            "device_id":     {"@id": "sosa:madeBySensor", "@type": "@id"},
                            "event_type":    {"@id": "sosa:observedProperty", "@type": "xsd:string"},
                            "motion_state":  {"@id": "pipeline:motionState", "@type": "xsd:string"},
                            "sequence_number": {"@id": "pipeline:sequenceNumber", "@type": "xsd:integer"},
                            "run_id":        {"@id": "pipeline:runId", "@type": "xsd:string"},
                            "observedIn":    {"@id": "pipeline:observedIn", "@type": "@id"}
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

                    # Publish to MQTT — the consumer receives this, adds latency, and writes to JSONL
                    client.publish(args.topic, json.dumps(record), qos=args.qos)

                    if last_ha_state != "detected":
                        client.publish(ha_motion_state_topic, "detected", qos=args.qos)
                        last_ha_state = "detected"

                    client.publish(ha_event_count_topic, str(seq), qos=args.qos)

                    if args.verbose:
                        print(f"[producer] SEQ {seq} | event: {event['kind']} | "
                              f"high_for: {event['high_for_s']:.2f}s | "
                              f"topic: {args.topic} | "
                              f"ha_count: {seq} → {ha_event_count_topic}")

            else:
                if last_ha_state == "detected":
                    client.publish(ha_motion_state_topic, "clear", qos=args.qos)
                    last_ha_state = "clear"

                    if args.verbose:
                        print(f"[producer] ha_state: clear → {ha_motion_state_topic}")

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
"""
virtual_sensor_rules.py

Connects to an MQTT broker, subscribes to motion event topics, maintains a
time-windowed count of events, and periodically publishes a usage level along
with event statistics to a dedicated topic.
"""

import json
import time
import argparse
from collections import deque
from threading import Lock
from datetime import datetime, timezone, timedelta
import os

import paho.mqtt.client as mqtt


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

event_times: deque = deque()        # stores UTC datetimes of "detected" events
event_lock: Lock = Lock()           # guards all access to event_times


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------

def on_connect(client: mqtt.Client, userdata, flags, rc: int) -> None:
    """Called when the client connects to the broker."""
    if rc == 0:
        print(f"[MQTT] Connected to broker (rc={rc})")
        topic = userdata["subscribe_topic"]
        client.subscribe(topic, qos=1)
        print(f"[MQTT] Subscribed to '{topic}'")
    else:
        print(f"[MQTT] Connection failed (rc={rc})")


def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage) -> None:
    """
    Called for every incoming message on the subscribed topic.

    Accepts two payload formats:
      • JSON object with a "hasSimpleResult" field  →  {"hasSimpleResult": "detected", ...}
      • Plain-text string                            →  "detected"
    """
    try:
        raw = message.payload.decode("utf-8").strip()

        # --- Try JSON first ---------------------------------------------------
        try:
            data = json.loads(raw)
            detected = str(data.get("motion_state", "")).strip().lower() == "detected"
        except (json.JSONDecodeError, AttributeError):
            # --- Fall back to plain-text --------------------------------------
            detected = raw.lower() == "detected"

        if detected:
            now = datetime.now(timezone.utc)
            with event_lock:
                event_times.append(now)
            # Uncomment for verbose per-event logging:
            # print(f"[EVENT] Motion detected at {now.isoformat()}")

    except Exception as exc:            # pragma: no cover – defensive catch
        print(f"[WARN] Could not process message: {exc}")


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------

def evaluate_usage(window_minutes: int = 10) -> tuple[str, int]:
    """
    Prune events older than *window_minutes* and return (usage_level, count).

    Thresholds
    ----------
    0          → "idle"
    1–5        → "low"
    6–15       → "medium"
    16+        → "high"
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    with event_lock:
        # Remove stale events from the left end of the deque
        while event_times and event_times[0] < cutoff:
            event_times.popleft()

        count = len(event_times)

    if count == 0:
        level = "idle"
    elif count <= 5:
        level = "low"
    elif count <= 15:
        level = "medium"
    else:
        level = "high"

    return level, count


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Virtual sensor rules: publish time-windowed usage levels via MQTT."
    )
    parser.add_argument(
    "--broker",
    default=os.environ.get("MQTT_BROKER", "localhost"),
    help="MQTT broker hostname or IP address (default: localhost)",
)
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)",
    )
    parser.add_argument(
        "--subscribe-topic",
        default="smartbin/bin-01/pir-01/events",
        help="Topic to subscribe to for raw motion events",
    )
    parser.add_argument(
        "--publish-topic",
        default="smartbin/bin-01/usage",
        help="Topic to publish usage-level summaries to",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=10,
        metavar="MINUTES",
        help="Length of the sliding time window in minutes (default: 10)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        metavar="SECONDS",
        help="Evaluation interval in seconds (default: 30)",
    )
    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # MQTT setup
    # -----------------------------------------------------------------------
    client = mqtt.Client(
        client_id="virtual-sensor-rules",
        userdata={"subscribe_topic": args.subscribe_topic},
    )
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[MQTT] Connecting to {args.broker}:{args.port} …")
    client.connect(args.broker, args.port)
    client.loop_start()             # non-blocking network thread

    print(
        f"\n[INFO] Monitoring started\n"
        f"       Subscribe topic : {args.subscribe_topic}\n"
        f"       Publish topic   : {args.publish_topic}\n"
        f"       Window          : {args.window} min\n"
        f"       Eval interval   : {args.interval} s\n"
    )

    # -----------------------------------------------------------------------
    # Evaluation loop
    # -----------------------------------------------------------------------
    try:
        while True:
            level, count = evaluate_usage(window_minutes=args.window)

            payload = json.dumps(
                {
                    "usageLevel":       level,
                    "eventCount":       count,
                    "windowMinutes":    args.window,
                    "evaluatedAt":      datetime.now(timezone.utc).isoformat(),
                },
                separators=(",", ":"),
            )

            client.publish(
                args.publish_topic,
                payload=payload,
                qos=1,
                retain=True,
            )

            print(
                f"[EVAL] level={level:<6}  events={count:>3}  "
                f"window={args.window}min  → published to '{args.publish_topic}'"
            )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user – shutting down.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("[MQTT] Disconnected.")


if __name__ == "__main__":
    main()
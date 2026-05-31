"""
virtual_sensor_ml.py

Loads a trained scikit-learn classifier and periodically publishes
a busy/quiet prediction for the next hour to an MQTT topic.
Also publishes an MQTT Discovery message so Home Assistant
automatically creates a sensor entity for the prediction.
"""

import json
import time
import argparse
from datetime import datetime, timezone

import joblib
import numpy as np
import paho.mqtt.client as mqtt


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(path: str):
    """Load the trained classifier from disk."""
    try:
        model = joblib.load(path)
        print(f"[MODEL] Loaded classifier from '{path}'")
        return model
    except FileNotFoundError:
        print(f"[ERROR] Model file not found at '{path}'")
        print("[ERROR] Run train_model.py first to generate the model.")
        raise


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def predict_next_hour(model) -> dict:
    """
    Build features for the next hour and return a prediction dict.

    Features
    --------
    day_of_week : int  0=Monday … 6=Sunday
    hour        : int  0–23 (the NEXT hour, not current)
    is_weekend  : int  1 if Saturday or Sunday, else 0
    """
    now          = datetime.now()
    next_hour    = (now.hour + 1) % 24
    day_of_week  = now.weekday()          # Monday=0, Sunday=6
    is_weekend   = 1 if day_of_week >= 5 else 0

    features = np.array([[day_of_week, next_hour, is_weekend]])

    prediction   = model.predict(features)[0]             # "busy" or "quiet"
    probabilities = model.predict_proba(features)[0]      # array of class probs
    classes      = list(model.classes_)                   # e.g. ["busy", "quiet"]
    confidence   = float(probabilities[classes.index(prediction)])

    return {
        "prediction":    prediction,
        "confidence":    round(confidence, 3),
        "next_hour":     next_hour,
        "day_of_week":   day_of_week,
        "is_weekend":    is_weekend,
        "predicted_at":  datetime.now(timezone.utc).isoformat(),
        "model":         "RandomForestClassifier",
        "features_used": {
            "day_of_week": day_of_week,
            "next_hour":   next_hour,
            "is_weekend":  is_weekend,
        }
    }


# ---------------------------------------------------------------------------
# Home Assistant MQTT Discovery
# ---------------------------------------------------------------------------

def publish_discovery(client: mqtt.Client, bin_id: str, qos: int) -> None:
    """
    Publish retained HA discovery messages so Home Assistant
    automatically creates entities for the ML prediction.
    """

    # --- 1. Prediction state sensor ---
    prediction_config = {
        "name":          "Activity Prediction",
        "state_topic":   f"smartbin/{bin_id}/prediction",
        "value_template":"{{ value_json.prediction }}",
        "json_attributes_topic": f"smartbin/{bin_id}/prediction",
        "icon":          "mdi:brain",
        "unique_id":     f"{bin_id}_ml_prediction",
        "device": {
            "identifiers": [bin_id],
            "name":        f"Smart Wastebin {bin_id}",
            "model":       "Smart Wastebin v1",
            "manufacturer":"ECE CK801 Team 03"
        }
    }
    client.publish(
        f"homeassistant/sensor/{bin_id}_ml_prediction/config",
        json.dumps(prediction_config),
        qos=qos,
        retain=True
    )

    # --- 2. Confidence sensor ---
    confidence_config = {
        "name":                 "Prediction Confidence",
        "state_topic":          f"smartbin/{bin_id}/prediction",
        "value_template":       "{{ value_json.confidence }}",
        "unit_of_measurement":  "%",
        "icon":                 "mdi:percent",
        "unique_id":            f"{bin_id}_ml_confidence",
        "device": {
            "identifiers": [bin_id],
            "name":        f"Smart Wastebin {bin_id}"
        }
    }
    client.publish(
        f"homeassistant/sensor/{bin_id}_ml_confidence/config",
        json.dumps(confidence_config),
        qos=qos,
        retain=True
    )

    print(f"[HA] Discovery messages published for device '{bin_id}'")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ML virtual sensor: predict next-hour activity and publish via MQTT."
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
        "--publish-topic",
        default="smartbin/bin-01/prediction",
        help="MQTT topic to publish predictions to",
    )
    parser.add_argument(
        "--model-path",
        default="models/busy_predictor.joblib",
        help="Path to the trained model file",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Prediction interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--bin-id",
        default="bin-01",
        help="Bin identifier used in MQTT topics and HA discovery",
    )
    parser.add_argument(
        "--qos",
        type=int,
        default=1,
        choices=[0, 1, 2],
        help="MQTT QoS level (default: 1)",
    )
    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # Load model
    # -----------------------------------------------------------------------
    model = load_model(args.model_path)

    # -----------------------------------------------------------------------
    # MQTT setup
    # -----------------------------------------------------------------------
    client = mqtt.Client(
        client_id="virtual-sensor-ml",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )

    print(f"[MQTT] Connecting to {args.broker}:{args.port} ...")
    client.connect(args.broker, args.port, keepalive=60)
    client.loop_start()

    # Publish HA discovery before the prediction loop
    publish_discovery(client, args.bin_id, args.qos)

    print(
        f"\n[INFO] ML virtual sensor started\n"
        f"       Publish topic : {args.publish_topic}\n"
        f"       Model         : {args.model_path}\n"
        f"       Interval      : {args.interval}s\n"
    )

    # -----------------------------------------------------------------------
    # Prediction loop
    # -----------------------------------------------------------------------
    try:
        while True:
            result = predict_next_hour(model)

            # Convert confidence to percentage for HA display
            result_for_publish = dict(result)
            result_for_publish["confidence"] = round(result["confidence"] * 100, 1)

            payload = json.dumps(result_for_publish, separators=(",", ":"))

            client.publish(
                args.publish_topic,
                payload=payload,
                qos=args.qos,
                retain=True
            )

            print(
                f"[PRED] next_hour={result['next_hour']:02d}:00  "
                f"prediction={result['prediction']:<5}  "
                f"confidence={result['confidence']*100:.1f}%  "
                f"day={result['day_of_week']}  "
                f"weekend={bool(result['is_weekend'])}"
            )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user — shutting down.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("[MQTT] Disconnected.")


if __name__ == "__main__":
    main()
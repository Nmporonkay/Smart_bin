import json
import os
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from flask import Flask
from flask_restx import Api, Resource, fields, reqparse

# ─────────────────────────────────────────
# 1. CONFIGURATION
# ─────────────────────────────────────────

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
EVENTS_FILE = os.path.join(BASE_DIR, "events.jsonl")
MODELS_DIR  = os.path.join(BASE_DIR, "models")

SENSOR_ID   = "urn:dev:team03:pir-01"
BIN_ID      = "urn:dev:team03:wastebin:bin-01"

# In-memory store for emptied records
emptied_log = []

# ─────────────────────────────────────────
# 2. DATA LOADING FUNCTIONS
# ─────────────────────────────────────────

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_events(filepath, limit=None, sensor_id=None):
    events = []

    if not os.path.exists(filepath):
        return events

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)

                # Skip the @context header line
                if "@context" in record and "@type" not in record:
                    continue

                # Filter by sensor_id if provided
                if sensor_id and record.get("device_id") != sensor_id:
                    continue

                events.append(record)

            except json.JSONDecodeError:
                continue

    # Most recent first
    events.reverse()

    if limit:
        events = events[:limit]

    return events


def load_bin_data():
    """Load wastebin model from JSON-LD file."""
    try:
        data = load_json(os.path.join(MODELS_DIR, "wastebin.jsonld"))
        return {
            "id": "bin-01",
            "uri": data.get("@id", BIN_ID),
            "name": data.get("schema:name", "Smart Wastebin 01"),
            "description": data.get("schema:description", ""),
            "material": data.get("schema:material", ""),
            "color": data.get("schema:color", ""),
            "capacity_liters": data.get("pipeline:capacityLiters", 0.48),
            "waste_type": data.get("pipeline:wasteType", "general"),
            "status": data.get("pipeline:status", "active"),
            "location": "Kypes Lab, University of Patras",
            "sensors": ["pir-01"]
        }
    except Exception:
        return {
            "id": "bin-01",
            "uri": BIN_ID,
            "name": "Smart Wastebin 01",
            "location": "Kypes Lab, University of Patras",
            "status": "active",
            "sensors": ["pir-01"]
        }


def load_sensor_data():
    """Load sensor model from JSON-LD file."""
    try:
        data = load_json(os.path.join(MODELS_DIR, "sensor.jsonld"))
        return {
            "id": "pir-01",
            "uri": data.get("@id", SENSOR_ID),
            "name": data.get("schema:name", "PIR Motion Sensor 01"),
            "model": data.get("pipeline:model", "HC-SR501"),
            "gpio_pin": data.get("pipeline:gpioPin", 17),
            "operating_voltage": data.get("pipeline:operatingVoltage", "5V"),
            "detection_range_m": data.get("pipeline:detectionRangeM", 1.5),
            "cooldown_seconds": data.get("pipeline:cooldownSeconds", 2.0),
            "status": data.get("pipeline:status", "active"),
            "mounted_on": "bin-01",
            "deployed_in": "urn:env:upatras:kypes-lab"
        }
    except Exception:
        return {
            "id": "pir-01",
            "uri": SENSOR_ID,
            "name": "PIR Motion Sensor 01",
            "model": "HC-SR501",
            "status": "active",
            "mounted_on": "bin-01"
        }


##MQTT##    

topic_store = {}
topic_lock  = threading.Lock()


def on_message(client, userdata, msg):
    with topic_lock:
        topic_store[msg.topic] = {
            "topic":     msg.topic,
            "payload":   msg.payload.decode("utf-8", errors="replace"),
            "qos":       msg.qos,
            "retain":    msg.retain,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


mqtt_client = mqtt.Client(
    client_id="wastebin-api",
    clean_session=False,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883, 60)
mqtt_client.subscribe("smartbin/#", qos=1)
mqtt_client.loop_start()



app = Flask(__name__)
api = Api(
    app,
    version="1.0",
    title="Smart Wastebin API",
    description="REST API for querying Smart Wastebin sensor data and bin status",
)



bin_model = api.model("Bin", {
    "id":               fields.String(required=True, description="Bin unique identifier"),
    "uri":              fields.String(description="Fully qualified URI from JSON-LD model"),
    "name":             fields.String(description="Human-readable name"),
    "location":         fields.String(description="Deployment location"),
    "status":           fields.String(description="Current status"),
    "material":         fields.String(description="Bin material"),
    "color":            fields.String(description="Bin color"),
    "capacity_liters":  fields.Float(description="Bin capacity in litres"),
    "waste_type":       fields.String(description="Type of waste accepted"),
    "sensors":          fields.List(fields.String, description="Sensor IDs mounted on this bin"),
})

event_model = api.model("Event", {
    "timestamp_utc":        fields.String(description="ISO timestamp of the event"),
    "device_id":            fields.String(description="Sensor URI that produced this event"),
    "event_type":           fields.String(description="Type of event"),
    "motion_state":         fields.String(description="Motion state (detected/clear)"),
    "sequence_number":      fields.Integer(description="Sequence number within this run"),
    "run_id":               fields.String(description="Pipeline run UUID"),
    "observedIn":           fields.String(description="Environment URI"),
    "ingest_time_utc":      fields.String(description="Time the consumer received the event"),
    "pipeline_latency_ms":  fields.Float(description="Pipeline latency in milliseconds"),
})

sensor_model = api.model("Sensor", {
    "id":                fields.String(required=True, description="Sensor unique identifier"),
    "uri":               fields.String(description="Fully qualified URI from JSON-LD model"),
    "name":              fields.String(description="Human-readable name"),
    "model":             fields.String(description="Hardware model"),
    "gpio_pin":          fields.Integer(description="GPIO pin number"),
    "operating_voltage": fields.String(description="Operating voltage"),
    "detection_range_m": fields.Float(description="Detection range in metres"),
    "cooldown_seconds":  fields.Float(description="Cooldown between detections"),
    "status":            fields.String(description="Current sensor status"),
    "mounted_on":        fields.String(description="Bin ID this sensor is mounted on"),
    "deployed_in":       fields.String(description="Environment URI"),
})

emptied_model = api.model("EmptiedRecord", {
    "bin_id":     fields.String(required=True, description="Bin identifier"),
    "emptied_at": fields.String(description="ISO timestamp of when the bin was emptied"),
    "emptied_by": fields.String(description="Who emptied the bin"),
})

publish_model = api.model("MQTTPublish", {
    "topic":   fields.String(required=True, description="MQTT topic to publish to"),
    "payload": fields.String(required=True, description="Message payload"),
    "qos":     fields.Integer(description="Quality of Service (0, 1, or 2)", default=1),
    "retain":  fields.Boolean(description="Retain this message on the broker", default=False),
})

topic_model = api.model("MQTTTopic", {
    "topic":     fields.String(description="MQTT topic"),
    "payload":   fields.String(description="Last received payload"),
    "qos":       fields.Integer(description="QoS level"),
    "retain":    fields.Boolean(description="Whether message was retained"),
    "timestamp": fields.String(description="Time the API received this message"),
})

# ─────────────────────────────────────────
# 6. QUERY PARAMETER PARSERS
# ─────────────────────────────────────────

events_parser = reqparse.RequestParser()
events_parser.add_argument(
    "limit", type=int, default=50,
    help="Maximum number of events to return"
)
events_parser.add_argument(
    "start", type=str,
    help="Filter events after this ISO datetime"
)
events_parser.add_argument(
    "end", type=str,
    help="Filter events before this ISO datetime"
)

# ─────────────────────────────────────────
# 7. BINS NAMESPACE
# ─────────────────────────────────────────

bins_ns = api.namespace("bins", description="Wastebin operations")

BINS_REGISTRY   = {"bin-01": load_bin_data()}
SENSOR_REGISTRY = {"pir-01": load_sensor_data()}


def find_bin(bin_id):
    return BINS_REGISTRY.get(bin_id)


def find_sensor(sensor_id):
    return SENSOR_REGISTRY.get(sensor_id)


def get_sensor_uri_for_bin(bin_id):
    """Return the device_id URI used in JSONL for this bin's sensor."""
    return SENSOR_ID


@bins_ns.route("/")
class BinList(Resource):
    @bins_ns.marshal_list_with(bin_model)
    def get(self):
        """List all registered bins."""
        return list(BINS_REGISTRY.values()), 200


@bins_ns.route("/<string:bin_id>")
@bins_ns.param("bin_id", "The bin identifier (e.g. bin-01)")
@bins_ns.response(404, "Bin not found")
class Bin(Resource):
    @bins_ns.marshal_with(bin_model)
    def get(self, bin_id):
        """Get details for a specific bin."""
        bin_data = find_bin(bin_id)
        if not bin_data:
            api.abort(404, f"Bin '{bin_id}' not found")
        return bin_data, 200


@bins_ns.route("/<string:bin_id>/sensors")
@bins_ns.param("bin_id", "The bin identifier")
@bins_ns.response(404, "Bin not found")
class BinSensors(Resource):
    @bins_ns.marshal_list_with(sensor_model)
    def get(self, bin_id):
        """List sensors mounted on a specific bin."""
        bin_data = find_bin(bin_id)
        if not bin_data:
            api.abort(404, f"Bin '{bin_id}' not found")
        sensors = [
            SENSOR_REGISTRY[s]
            for s in bin_data.get("sensors", [])
            if s in SENSOR_REGISTRY
        ]
        return sensors, 200


@bins_ns.route("/<string:bin_id>/events")
@bins_ns.param("bin_id", "The bin identifier")
@bins_ns.response(404, "Bin not found")
@bins_ns.response(400, "Invalid query parameters")
class BinEvents(Resource):
    @bins_ns.expect(events_parser)
    @bins_ns.marshal_list_with(event_model)
    def get(self, bin_id):
        """Get motion events for a specific bin."""
        bin_data = find_bin(bin_id)
        if not bin_data:
            api.abort(404, f"Bin '{bin_id}' not found")

        args       = events_parser.parse_args()
        limit      = args["limit"]
        start      = args["start"]
        end        = args["end"]
        sensor_uri = get_sensor_uri_for_bin(bin_id)

        events = load_events(EVENTS_FILE, limit=None, sensor_id=sensor_uri)

        # Apply datetime filters if provided
        if start:
            try:
                start_dt = datetime.fromisoformat(start)
                events = [
                    e for e in events
                    if datetime.fromisoformat(
                        e.get("timestamp_utc", "1970-01-01T00:00:00+00:00")
                    ) >= start_dt
                ]
            except ValueError:
                api.abort(400, "Invalid 'start' datetime format. Use ISO 8601.")

        if end:
            try:
                end_dt = datetime.fromisoformat(end)
                events = [
                    e for e in events
                    if datetime.fromisoformat(
                        e.get("timestamp_utc", "1970-01-01T00:00:00+00:00")
                    ) <= end_dt
                ]
            except ValueError:
                api.abort(400, "Invalid 'end' datetime format. Use ISO 8601.")

        return events[:limit], 200


@bins_ns.route("/<string:bin_id>/emptied")
@bins_ns.param("bin_id", "The bin identifier")
@bins_ns.response(201, "Bin marked as emptied")
@bins_ns.response(404, "Bin not found")
class BinEmptied(Resource):
    @bins_ns.expect(emptied_model)
    def post(self, bin_id):
        """Record that a bin was emptied and publish MQTT status update."""
        bin_data = find_bin(bin_id)
        if not bin_data:
            api.abort(404, f"Bin '{bin_id}' not found")

        data = api.payload or {}

        record = {
            "bin_id":     bin_id,
            "emptied_at": data.get(
                "emptied_at",
                datetime.now(timezone.utc).isoformat()
            ),
            "emptied_by": data.get("emptied_by", "unknown"),
        }

        emptied_log.append(record)

        # Publish MQTT status update so Home Assistant and consumers hear about it
        mqtt_payload = json.dumps({
            "state":      "emptied",
            "emptied_at": record["emptied_at"]
        })
        mqtt_client.publish(
            f"smartbin/{bin_id}/status",
            mqtt_payload,
            qos=1,
            retain=True
        )

        return record, 201


# ─────────────────────────────────────────
# 8. SENSORS NAMESPACE
# ─────────────────────────────────────────

sensors_ns = api.namespace("sensors", description="Sensor operations")


@sensors_ns.route("/")
class SensorList(Resource):
    @sensors_ns.marshal_list_with(sensor_model)
    def get(self):
        """List all registered sensors."""
        return list(SENSOR_REGISTRY.values()), 200


@sensors_ns.route("/<string:sensor_id>")
@sensors_ns.param("sensor_id", "The sensor identifier (e.g. pir-01)")
@sensors_ns.response(404, "Sensor not found")
class Sensor(Resource):
    @sensors_ns.marshal_with(sensor_model)
    def get(self, sensor_id):
        """Get details for a specific sensor."""
        sensor = find_sensor(sensor_id)
        if not sensor:
            api.abort(404, f"Sensor '{sensor_id}' not found")
        return sensor, 200


# ─────────────────────────────────────────
# 9. MQTT NAMESPACE
# ─────────────────────────────────────────

mqtt_ns = api.namespace("mqtt", description="MQTT broker interaction")


@mqtt_ns.route("/publish")
class MQTTPublish(Resource):
    @mqtt_ns.expect(publish_model)
    @mqtt_ns.response(200, "Message published")
    @mqtt_ns.response(400, "Invalid request")
    def post(self):
        """Publish a message to an MQTT topic."""
        data    = api.payload or {}
        topic   = data.get("topic")
        payload = data.get("payload")
        qos     = data.get("qos", 1)
        retain  = data.get("retain", False)

        if not topic or not payload:
            api.abort(400, "Both 'topic' and 'payload' are required")

        if qos not in (0, 1, 2):
            api.abort(400, "QoS must be 0, 1, or 2")

        result = mqtt_client.publish(topic, payload, qos=qos, retain=retain)

        return {
            "status":  "published",
            "topic":   topic,
            "payload": payload,
            "qos":     qos,
            "retain":  retain,
            "mqtt_rc": result.rc
        }, 200


@mqtt_ns.route("/topics")
class MQTTTopics(Resource):
    @mqtt_ns.response(200, "List of tracked topics")
    def get(self):
        """List all known MQTT topics and their last received message."""
        with topic_lock:
            return {
                "topic_count": len(topic_store),
                "topics":      list(topic_store.values())
            }, 200


@mqtt_ns.route("/topics/<path:topic>")
@mqtt_ns.param("topic", "MQTT topic path (e.g. smartbin/bin-01/pir-01/motion)")
@mqtt_ns.response(404, "Topic not found or no message received yet")
class MQTTTopicDetail(Resource):
    def get(self, topic):
        """Get the last received message for a specific MQTT topic."""
        with topic_lock:
            entry = topic_store.get(topic)
            if not entry:
                api.abort(404, f"No message received on topic '{topic}'")
            return entry, 200


# ─────────────────────────────────────────
# 10. RUN
# ─────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
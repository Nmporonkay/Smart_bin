FROM python:3.11-slim

WORKDIR /app

COPY ml_model/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ml_model/ .

# Train the model at build time so it is baked into the image.
# Both virtual-sensor-rules and virtual-sensor-ml use this same image;
# docker-compose overrides CMD per service.
RUN python train_model.py

CMD ["python", "virtual_sensor_rules.py"]

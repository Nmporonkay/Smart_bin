Section A - Instructions to run the code

1. Set up the wiring of the Raspberry Pi and the sensor
components: at least 3 Female-to-female jumper wires
            PIR motion sensor
            Raspberry Pi 5

A. How to connect the sensor
Using the following images to understand in what way to hold the Pi
![My Image](images/image1.png)
![My Image](images/image2.png)
![My Image](images/image3.png)

connect: VCC (sensor) in pin number 4 (Pi)
         GND (sensor) in pin number 34 (Pi)
         OUT (sensor) in pin number 15 (Pi)

* Power down and unplug Pi while doing the wiring
* After turning Pi back on wait a 60sec warm up period each time

2. Docker Installation
make sure the following are install with commands
docker --version
docker compose version
or install with command
curl -fsSL https://get.docker.com | sh

3. Run as root
use command
sudo usermod -aG docker $USER
and do a full system reboot in order to run the Docker daemon as root
check it work with commands
groups
docker run hello-world

4. Build the image
enter the correct path cd labs/lab04/ 
and run command
docker build -t motion-pipeline .

5. Run the container
create a local directory for the output with command
mkdir -p output
and then run the container with command
docker run --rm \
  --privileged \
  --device /dev/gpiomem0:/dev/gpiomem \
  --device /dev/gpiochip0:/dev/gpiochip0 \
  -v $(pwd)/output:/data \
  motion-pipeline

6. Run the programm 
an example with some default parameters follows

docker run --rm \
  --privileged \
  --device /dev/gpiomem0:/dev/gpiomem \
  --device /dev/gpiochip0:/dev/gpiochip0 \
  -v $(pwd)/output:/data \
  motion-pipeline \
  python run_pipeline.py \
  --device-id pir-docker-01 \
  --pin 4 \
  --sample-interval 0.1 \
  --cooldown 5 \
  --min-high 0.2 \
  --queue-size 50 \
  --consumer-delay 0.5 \
  --duration 6000 \
  --out /data/motion_pipeline.jsonl \
  --verbose

7. Run with Docker Compose
use command
docker compose up --build
to build the image

and to stop it use command
docker compose down

or to stop and remove the volumes use command
docker compose down -v


Section B - Questions

RQ1: What base image did you use and why?

We used python slim because it's lighter than regular python and it has all the libraries we need 

RQ2: How many layers does your Dockerfile create? Which instructions produce new layers?

The dockerfile has 7 instructions. Every instruction is a new layer, so the dockerfile has 7 layers

FROM python:3.11-slim
WORKDIR /home/iotlab_upat_3/labs/Labs_Advanced_Techniques/labs/lab04
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pirlib ./pirlib
COPY run_pipeline.py .
CMD python run_pipeline.py \
    --device-id pir-01 \
    --pin 17 \
    --sample-interval 0.1 \
    --cooldown-s 2 \
    --min-high-s 0.5 \
    --queue-size 100 \
    --consumer-delay 0.0 \
    --duration 60 \
    --out motion_pipeline.jsonl \
    --verbose

RQ3: What is the size of your built image?

![My Image](images/RQ1.png)

RQ4: Why do we copy requirements.txt and install dependencies before copying the rest of the code? What would happen if we reversed the order?

Because of docker's layer caching. If the order was in reverse, the dependencies would be reinstelled every time the code changes

RQ5:What does --device /dev/gpiomem do and why is it needed?

--device /dev/gpiomem gives the container access to GPIO hardware. Without it, the PIR sensor cannot be read from the container

RQ6: What happens to the JSONL output if you run the container without a volume mount (-v)?
The output file is created inside the container’s filesystem. When the container stops, its data is deleted, so the JSONL output is lost.

RQ7: Did the pipeline behave the same inside Docker as it did running directly on the Pi in Lab 03? Any differences?

The pipeline ran a little slower than it did in lab03, possibly due to microdelays, but the handling of the dependencies was a lot easier

RQ8: What happened when you set --memory=32m? Does this work on the Pi? Why or why not?
In many cases, memory limits do not work reliably on the Raspberry Pi due to limitations in cgroup configuration.
If enforced, the container may be killed with exit code 137 when it exceeds the memory limit

RQ9: Why are resource limits important on edge devices in general?
Resource limits are important because edge devices have limited CPU and memory. They prevent a single process from consuming all resources, help maintain system stability, and protect against crashes.

RQ10: What is the advantage of writing a docker-compose.yml instead of using docker run with flags?
Docker Compose allows you to define the entire configuration in a single file, making it easier to manage. It's also easier to run because it requires simpler commands to run with 1-2 flags at most

RQ11: What is the difference between a bind mount (-v $(pwd)/output:/data) and a named volume (pipeline-data:/data)?

Bind mount:
Links a local directory to the container. Files are directly accessible on the host system.
Named volume:
Managed by Docker. It is more portable and independent of the current directory but not directly visible without Docker tools.

RQ12: What does restart: unless-stopped do and why does it matter for an edge device?
This setting ensures the container automatically restarts if it crashes or the system reboots, unless it is manually stopped.
It is important for edge devices because they often run unattended and must recover automatically from failures.

RQ13: What does a virtual environment isolate, and what does it not isolate?

A virtual environment isolates python packages and dependencies, but it doesn't isolate: the OS, system libraries and kernell or hardware access



RQ14: Give one concrete example where a requirements.txt and a venv would not be enough to reproduce your Lab 03 setup on a different machine.
If the application depends on system-level libraries or hardware-specific drivers (e.g., GPIO access on Raspberry Pi), a virtual environment alone is not enough, because it does not include those system dependencies.


RQ15: Give one scenario where a virtual environment is perhaps a better choice than Docker.
During development, a virtual environment is often better because it is faster to set up, uses fewer resources, and makes debugging easier.


RQ16: In the context of the Smart Wastebin project, which approach (venv or Docker) would you prefer to use for a final deployment, and why?
Docker is preferable for final deployment because it ensures a consistent environment across devices, supports multiple services (e.g., sensors, MQTT, dashboard), and is more reliable for edge deployments.

Images of running our code
![My Image](images/docker-run.png)
![My Image](images/docker-run2.png)
![My Image](images/docker-ps.png)
![My Image](images/limit-cpu.png)
![My Image](images/limit-cpu2.png)
![My Image](images/limit-memory.png)
Alright. If you are here it means you want to run our program, so let's see how to do that. 

At first, you need a sensor, such as HC‑SR501, or any other sensor in fact, that connects to a Rasberry Pi operating system, or any other os, and the source code, with the exact paths the same as presented in the repository. 

Connect three wires from the sensor as follows:

- left(ground) ===> ground
- middle(output) ===> gpio pin 17
- right(+power) ===> 5V

![alt text](image.png)

Next thing you need to do, is connect through your terminal via ssh. You have to know the ip address of your pi. 
Just type: 


- ssh username_in_pi@123.456.78.9


in your terminal.

Once your in, you have to change the working directory. 
Type: 

cd home_or_whatever/path_to_where_you_git-pulled 

Next being thing is one important command: 

docker compose up --build

this builds the entire application, from start to finish. 
Congratulations! You launched our project. 

It downloads anything you don't have, and launches everything. 
--build is not a necessary part of the command, but it rebuilds the whole docker image everytime. If you haven't made locally any change, docker compose up should be alright. 

NOW: 
If you ACTUALLY want to use it, there's a bit more...

You can see many types of messages from the program, if you subscribe to the right topic, according to our setted structure. 

These lines, show the most important messages you can get. What you will see after that is easily assesed. + means that you subscribe to all the possible topics one layer ahead, and # means that you subscribe to all possible topics all layers ahead. 

smartbin/{bin-id}/{sensor-id}/{message-type}

mosquitto_sub -h localhost -t "smartbin/#" -v

mosquitto_sub -h localhost -t "smartbin/bin-01/pir-01/events" -v

mosquitto_sub -h localhost -t "smartbin/bin-01/+/events" -v

mosquitto_sub -h localhost -t "smartbin/+/pir-01/events" -v

mosquitto_sub -h localhost -t "smartbin/bin-01/usage" -v

mosquitto_sub -h localhost -t "smartbin/bin-01/prediction" -v

mosquitto_sub -h localhost -t "smartbin/bin-01/+" -v

Here's a diagram of the structure, so that you know how to go anywhere. 


smartbin
│
├── bin-01
│   │
│   ├── pir-01
│   │   └── events
│   │       └── Raw motion events (JSON-LD)
│   │
│   ├── usage
│   │   └── Rules-based usage level
│   │
│   └── prediction
│       └── ML future activity prediction
│
├── bin-02
│   └── ...
│
└── bin-N
    └── ...

That's pretty much it. As long as you connected everything correctly and followed the instructions faithfully, everything should be working fine. 

If you want to go go EVEN FURTHER, stay with me. 
In the working directory, run:
python analyze.py

in, a directory named charts, you will see your results. They will help you after a long time, if you want to make statistical analysis for the events the sensor detects. 

If you want to see what is going on on Home Assistant, click http://<your-pi-ip>:8123 on your browser. There you will configure your system after you make your account, or paste our own configuration, if you find it practical. It's missing home_assistant_core.yml, so you 'll have to make sth of your own. 

To see your model built in Node-Red, click http:/<your-pi-ip>:1880

And, if you want to see your data live resting on REST-API, click  http://<your-pi-ip>:5000 

That, was all, enjoy. 

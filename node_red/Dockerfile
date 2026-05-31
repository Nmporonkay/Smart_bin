FROM nodered/node-red:latest

USER root

RUN npm install --prefix /usr/src/node-red node-red-dashboard@3.6.6

COPY flows.json /data/flows.json

USER node-red

CMD ["node-red", "--userDir", "/data", "--flowFile", "/usr/src/node-red/flows.json"]
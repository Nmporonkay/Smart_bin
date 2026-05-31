FROM nodered/node-red:latest

USER root

# Install node-red-dashboard (the AngularJS version used by the flows)
RUN npm install --prefix /usr/src/node-red node-red-dashboard@3.6.6

# Copy your flows file directly into the image as the standard default fallback
COPY flows.json /usr/src/node-red/flows.json


# Switch back to the standard secure user
USER node-red
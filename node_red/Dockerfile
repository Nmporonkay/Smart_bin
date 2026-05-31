FROM nodered/node-red:latest

USER root

# Install node-red-dashboard (the AngularJS version used by the flows)
RUN npm install --prefix /usr/src/node-red node-red-dashboard@3.6.6

# Copy the default flows to a non-volume path so the file survives volume mounts.
# /data is declared as VOLUME in the base image, so files written there during
# the build are discarded at runtime. We keep the template outside /data and
# copy it into /data on first start via the node-red-start script below.
COPY node_red/flows.json /flows_default.json
RUN chmod 644 /flows_default.json

# Create the node-red-start wrapper script.
# On first run it seeds /data/flows.json from the baked-in template.
# On subsequent runs it leaves any user-edited flows in place.
RUN printf '#!/bin/sh\n\
if [ ! -f /data/flows.json ]; then\n\
    echo "[node-red-start] seeding flows from template"\n\
    cp /flows_default.json /data/flows.json\n\
fi\n\
exec node-red --flowFile /data/flows.json --userDir /data\n' \
    > /usr/local/bin/node-red-start \
 && chmod +x /usr/local/bin/node-red-start

USER node-red

# Clear the parent ENTRYPOINT so CMD runs directly
ENTRYPOINT []
CMD ["node-red-start"]

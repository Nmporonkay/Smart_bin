FROM nodered/node-red:latest

USER root

# Install node-red-dashboard (the AngularJS version used by the flows)
RUN npm install --prefix /usr/src/node-red node-red-dashboard@3.6.6

# ─── FIXED PATH: Save the template file directly to the root namespace ───
COPY flows.json /flows_default.json
RUN chmod 644 /flows_default.json
# ─────────────────────────────────────────────────────────────────────────

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

# Fix permissions so the internal node-red user owns our boot scripts
RUN chown -R node-red:node-red /data /flows_default.json /usr/local/bin/node-red-start

USER node-red

# Clear the parent ENTRYPOINT so CMD runs directly
ENTRYPOINT []
CMD ["node-red-start"]
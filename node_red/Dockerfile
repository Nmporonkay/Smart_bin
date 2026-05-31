FROM nodered/node-red:latest

USER root

# Install node-red-dashboard (the AngularJS version used by the flows)
RUN npm install --prefix /usr/src/node-red node-red-dashboard@3.6.6

# ─── FIXED PATH: Save the template file directly to the root namespace ───
COPY node_red/flows.json /usr/src/node-red/flows.json

# Fix permissions so the internal node-red user owns our boot scripts

USER node-red

# Clear the parent ENTRYPOINT so CMD runs directly
ENTRYPOINT []
CMD ["node-red-start"]
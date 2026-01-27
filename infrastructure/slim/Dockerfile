# SLIM Gateway for Azure Container Instances
# Custom image with embedded configuration
#
# SLIM (Secure Low-Latency Interactive Messaging) provides the A2A protocol
# transport layer for agent-to-agent communication in the AGNTCY framework.
#
# Build: docker build -t slim-gateway:latest -f infrastructure/slim/Dockerfile .
# Run:   docker run -p 8443:8443 slim-gateway:latest

FROM ghcr.io/agntcy/slim:0.6.1

# Copy the SLIM configuration file
COPY config/slim/azure-server-config.yaml /config.yaml

# Set the default command
CMD ["/slim", "--config", "/config.yaml"]

# Expose SLIM's gRPC port
EXPOSE 8443

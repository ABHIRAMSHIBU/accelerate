#!/bin/bash
# Health check script for podman containers
# Usage: health_check_podman.sh container1 container2 ...

if [ $# -eq 0 ]; then
    echo "Usage: $0 container1 container2 ..."
    exit 1
fi

ALL_HEALTHY=true

for container in "$@"; do
    echo "Checking container: $container"
    
    # Check if container exists
    if ! podman ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
        echo "UNHEALTHY: Container $container does not exist"
        ALL_HEALTHY=false
        continue
    fi
    
    # Check if container is running
    if ! podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
        echo "UNHEALTHY: Container $container exists but is not running"
        ALL_HEALTHY=false
        continue
    fi
    
    # Container exists and is running
    echo "HEALTHY: Container $container is running"
done

if [ "$ALL_HEALTHY" = true ]; then
    echo "All containers are healthy"
    exit 0
else
    echo "One or more containers are unhealthy"
    exit 1
fi
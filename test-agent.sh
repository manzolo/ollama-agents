#!/bin/bash

# Test script for swarm-converter agent

if [ -z "$1" ]; then
    echo "Usage: $0 <docker-compose.yml>"
    echo ""
    echo "Example:"
    echo "  $0 test-compose.yml"
    exit 1
fi

COMPOSE_FILE="$1"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: File '$COMPOSE_FILE' not found"
    exit 1
fi

echo "Converting $COMPOSE_FILE to Docker Swarm stack file..."
echo ""

# Create JSON payload
CONTENT=$(cat "$COMPOSE_FILE" | jq -Rs .)

# Make the API request
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d "{\"input\": $CONTENT}" \
  -s | jq -r '.output'

echo ""
echo "---"
echo "Conversion complete!"

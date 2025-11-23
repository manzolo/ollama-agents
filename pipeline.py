#!/usr/bin/env python3
"""
Agent Pipeline Orchestrator
Chains swarm-converter and swarm-validator agents.
"""

import argparse
import sys
import json
import requests
from pathlib import Path

# Configuration
CONVERTER_URL = "http://localhost:7001/process/raw"
VALIDATOR_URL = "http://localhost:7002/process/raw"

def process_agent(url, input_text, agent_name):
    """Send input to an agent and get the response."""
    print(f"Sending to {agent_name}...")
    try:
        response = requests.post(
            url,
            json={"input": input_text},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("output")
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with {agent_name}: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Run Agent Pipeline")
    parser.add_argument("--file", required=True, help="Path to input docker-compose.yml")
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: File '{input_path}' not found.")
        sys.exit(1)

    # Step 1: Read Input
    print(f"Reading {input_path}...")
    with open(input_path, "r") as f:
        input_content = f.read()

    # Step 2: Convert (Swarm Converter)
    swarm_stack = process_agent(CONVERTER_URL, input_content, "Swarm Converter")
    
    print("\n--- Generated Swarm Stack ---\n")
    print(swarm_stack)
    print("\n-----------------------------\n")

    # Step 3: Validate (Swarm Validator)
    validation_result = process_agent(VALIDATOR_URL, swarm_stack, "Swarm Validator")

    print("\n--- Validation Result ---\n")
    try:
        # Try to parse as JSON for pretty printing
        parsed = json.loads(validation_result)
        print(json.dumps(parsed, indent=2))
    except json.JSONDecodeError:
        print(validation_result)
    print("\n-------------------------\n")

if __name__ == "__main__":
    main()

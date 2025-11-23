#!/usr/bin/env python3
"""
Orchestrator Agent
Acts as an API Gateway to chain other agents.
"""

import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uvicorn

app = FastAPI(title="Orchestrator Agent")

# Configuration
SWARM_CONVERTER_URL = os.getenv("SWARM_CONVERTER_URL", "http://agent-swarm-converter:8000/process/raw")
SWARM_VALIDATOR_URL = os.getenv("SWARM_VALIDATOR_URL", "http://agent-swarm-validator:8000/process/raw")

class AgentRequest(BaseModel):
    input: str
    options: Optional[Dict[str, Any]] = None

@app.post("/process")
async def process(request: AgentRequest):
    """
    Orchestrates the pipeline:
    1. Input -> Swarm Converter
    2. Swarm Stack -> Swarm Validator
    3. Return Validation Result
    """
    timeout = httpx.Timeout(300.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Step 1: Convert
        try:
            print(f"Sending to Swarm Converter: {SWARM_CONVERTER_URL}")
            converter_response = await client.post(
                SWARM_CONVERTER_URL,
                json={"input": request.input}
            )
            converter_response.raise_for_status()
            swarm_stack = converter_response.json().get("output")
            
            if not swarm_stack:
                raise HTTPException(status_code=500, detail="Swarm Converter returned empty output")

        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Error communicating with Swarm Converter: {e}")

        # Step 2: Validate
        try:
            print(f"Sending to Swarm Validator: {SWARM_VALIDATOR_URL}")
            validator_response = await client.post(
                SWARM_VALIDATOR_URL,
                json={"input": swarm_stack}
            )
            validator_response.raise_for_status()
            validation_result = validator_response.json()
            
            # The validator returns a RawResponse structure from the base agent, 
            # or sometimes just the raw JSON if we used /process/raw correctly.
            # Let's just return what the validator gave us, but wrap it in a standard response format
            # if needed, or just return it directly.
            
            return {
                "agent": "orchestrator",
                "output": validation_result.get("output", str(validation_result)),
                "model": "orchestrator-logic",
                "timestamp": "now"
            }

        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Error communicating with Swarm Validator: {e}")

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "orchestrator"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

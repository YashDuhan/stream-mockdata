from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import json
import asyncio
import uvicorn
from typing import Dict, Any, List
import os

app = FastAPI(title="JSON Streamer", 
              description="streaming JSON content")

@app.get("/")
async def root():
    return {"message": "Welcome to JSON Streamer"}

@app.get("/test", summary="Stream main.json", 
         description="endpoint that streams main.json")
async def test():
    try:
        with open("main.json", "r") as file:
            content = file.read()
    except FileNotFoundError:
        return {"error": "Could not load main.json file"}
    
    async def generate():
        # Stream with a small delay
        for char in content:
            yield char
            await asyncio.sleep(0.01)  # delay 
    
    return StreamingResponse(generate(), media_type="application/json")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
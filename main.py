from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import uvicorn
from typing import Dict, Any, List
import os

app = FastAPI(title="JSON Streamer", 
              description="streaming JSON content")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
async def root():
    return {"message": "Welcome to JSON Streamer"}

@app.get("/test", summary="Stream main.json", 
         description="endpoint that streams main.json in LLM-like format")
async def test():
    try:
        with open("main.json", "r") as file:
            content = file.read()
    except FileNotFoundError:
        # For Vercel deployment, use absolute path
        try:
            current_dir = os.path.dirname(os.path.realpath(__file__))
            with open(os.path.join(current_dir, "main.json"), "r") as file:
                content = file.read()
        except FileNotFoundError:
            return {"error": "Could not load main.json file"}
    
    async def generate():
        # Process the content in larger chunks to reduce total number of chunks
        buffer = ""
        for char in content:
            buffer += char
            # Increased chunk size to 10 characters or natural boundaries
            if len(buffer) >= 10 or char in ['}', ']', ',', ';', '.', ':', '\n']:
                # Format in OpenAI-like delta format
                chunk = json.dumps({
                    "choices": [{
                        "delta": {
                            "content": buffer
                        }
                    }]
                })
                yield f"data: {chunk}\n\n"
                # Increased delay to 0.2 seconds between chunks
                await asyncio.sleep(0.2)
                buffer = ""
        
        # Send any remaining buffer
        if buffer:
            chunk = json.dumps({
                "choices": [{
                    "delta": {
                        "content": buffer
                    }
                }]
            })
            yield f"data: {chunk}\n\n"
        
        # End of stream marker
        chunk = json.dumps({
            "choices": [{
                "delta": {}
            }]
        })
        yield f"data: {chunk}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 

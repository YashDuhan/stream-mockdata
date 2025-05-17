from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import uvicorn
from typing import Dict, Any, List
import os
from pydantic import BaseModel

class GenerateRequest(BaseModel):
    prompt: str

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
    async def generate():
        data = None
        try:
            # Try reading from the standard path first
            with open("main.json", "r") as file:
                content_str = file.read()
            data = json.loads(content_str)
        except FileNotFoundError:
            # If not found, try the Vercel deployment path
            try:
                current_dir = os.path.dirname(os.path.realpath(__file__))
                alt_path = os.path.join(current_dir, "main.json")
                with open(alt_path, "r") as file:
                    content_str = file.read()
                data = json.loads(content_str)
            except FileNotFoundError:
                error_payload_str = json.dumps({"error": "Could not load main.json file"})
                error_chunk_payload = {"data": error_payload_str}
                yield f"data: {json.dumps(error_chunk_payload)}\\n\\n"
                eos_marker_payload = {"data": None}
                yield f"data: {json.dumps(eos_marker_payload)}\\n\\n"
                return
            except json.JSONDecodeError:
                error_payload_str = json.dumps({"error": f"main.json at {alt_path} is not valid JSON"})
                error_chunk_payload = {"data": error_payload_str}
                yield f"data: {json.dumps(error_chunk_payload)}\\n\\n"
                eos_marker_payload = {"data": None}
                yield f"data: {json.dumps(eos_marker_payload)}\\n\\n"
                return
        except json.JSONDecodeError:
            error_payload_str = json.dumps({"error": "main.json is not valid JSON"})
            error_chunk_payload = {"data": error_payload_str}
            yield f"data: {json.dumps(error_chunk_payload)}\\n\\n"
            eos_marker_payload = {"data": None}
            yield f"data: {json.dumps(eos_marker_payload)}\\n\\n"
            return

        current_data_accumulator = None
        initial_empty_yielded = False

        if isinstance(data, dict):
            current_data_accumulator = {}
        elif isinstance(data, list):
            current_data_accumulator = []
        else:
            # For primitive types, the accumulator will be the data itself.
            current_data_accumulator = data


        # Yield initial empty state for dict/list if applicable
        if isinstance(data, (dict, list)):
            chunk_content_str = json.dumps(current_data_accumulator)
            chunk_to_send_payload = {"data": chunk_content_str}
            yield f"data: {json.dumps(chunk_to_send_payload)}\\n\\n"
            await asyncio.sleep(2.5)
            initial_empty_yielded = True

        # Process and stream data
        if isinstance(data, dict):
            keys = list(data.keys())
            for key in keys:
                current_data_accumulator[key] = data[key]
                chunk_content_str = json.dumps(current_data_accumulator)
                chunk_to_send_payload = {"data": chunk_content_str}
                yield f"data: {json.dumps(chunk_to_send_payload)}\\n\\n"
                await asyncio.sleep(2.5)
        elif isinstance(data, list):
            for item in data:
                current_data_accumulator.append(item)
                chunk_content_str = json.dumps(current_data_accumulator)
                chunk_to_send_payload = {"data": chunk_content_str}
                yield f"data: {json.dumps(chunk_to_send_payload)}\\n\\n"
                await asyncio.sleep(2.5)
        else: # Primitive type (string, number, boolean, null)
            if not initial_empty_yielded:
                chunk_content_str = json.dumps(current_data_accumulator) # current_data_accumulator is data
                chunk_to_send_payload = {"data": chunk_content_str}
                yield f"data: {json.dumps(chunk_to_send_payload)}\\n\\n"
                await asyncio.sleep(2.5)
        
        # End of stream marker
        eos_marker_payload = {"data": None}
        yield f"data: {json.dumps(eos_marker_payload)}\\n\\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/generate", summary="Stream data incrementally based on prompt", 
         description="Endpoint that streams data incrementally, building up a complete JSON object")
async def generate(request: GenerateRequest):
    async def stream_generator():
        data = None
        try:
            # Try reading from the standard path first
            with open("main.json", "r") as file:
                content_str = file.read()
            data = json.loads(content_str)
        except FileNotFoundError:
            # If not found, try the Vercel deployment path
            try:
                current_dir = os.path.dirname(os.path.realpath(__file__))
                alt_path = os.path.join(current_dir, "main.json")
                with open(alt_path, "r") as file:
                    content_str = file.read()
                data = json.loads(content_str)
            except FileNotFoundError:
                error_json = json.dumps({"error": "Could not load main.json file"})
                yield f"{error_json}\\n"
                return
            except json.JSONDecodeError:
                error_json = json.dumps({"error": f"main.json at {alt_path} is not valid JSON"})
                yield f"{error_json}\\n"
                return
        except json.JSONDecodeError:
            error_json = json.dumps({"error": "main.json is not valid JSON"})
            yield f"{error_json}\\n"
            return

        # The full data structure as an accumulator
        accumulated_data = {}

        # Process top-level keys one by one
        sections = list(data.keys())
        
        # First send an empty JSON object
        yield "{}\\n"
        await asyncio.sleep(1)

        # Then start adding sections one by one
        for section in sections:
            # Add the current section to the accumulated data
            accumulated_data[section] = data[section]
            
            # Return the accumulated JSON
            yield f"{json.dumps(accumulated_data)}\\n"
            
            # Delay before sending the next chunk
            await asyncio.sleep(2.5)
    
    return StreamingResponse(
        stream_generator(), 
        media_type="text/plain"  # Changed to text/plain since we're not using SSE format
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8888, reload=True) 

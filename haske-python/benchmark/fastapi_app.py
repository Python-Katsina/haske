from fastapi import FastAPI, Request
import asyncio
import json

app = FastAPI()

@app.get("/json")
async def json_endpoint():
    return {"message": "Hello, FastAPI"}

@app.get("/query")
async def query_endpoint(name: str = "World"):
    return {"hello": name}

@app.get("/headers")
async def headers_endpoint(request: Request):
    return {"user-agent": request.headers.get("user-agent", "unknown")}

@app.post("/post_small")
async def post_small(data: dict):
    return {"received": data}

@app.post("/post_large")
async def post_large(data: dict):
    return {"size": len(json.dumps(data))}

@app.get("/large_resp")
async def large_resp():
    big_text = "X" * 1000000
    return {"data": big_text}

@app.get("/compute")
async def compute():
    def fib(n: int) -> int:
        if n <= 1:
            return n
        return fib(n - 1) + fib(n - 2)
    return {"fib": fib(20)}

@app.get("/sleep")
async def sleep(secs: float = 0.1):
    await asyncio.sleep(secs)
    return {"slept": secs}

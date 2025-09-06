from haske import Haske, Request, Response
import asyncio
import json

app = Haske(__name__)

@app.route("/json")
async def json_endpoint(request: Request):
    return {"message": "Hello, Haske"}

@app.route("/query")
async def query_endpoint(request: Request):
    name = request.query_params.get("name", "World")
    return {"hello": name}

@app.route("/headers")
async def headers_endpoint(request: Request):
    user_agent = request.headers.get("user-agent", "unknown")
    return {"user-agent": user_agent}

@app.route("/post_small", methods=["POST", "PUT"])
async def post_small(request: Request):
    data = await request.json()
    return {"received": data}

@app.route("/post_large", methods=["POST", "PUT"])
async def post_large(request: Request):
    data = await request.json()
    return {"size": len(json.dumps(data))}

@app.route("/large_resp")
async def large_resp(request: Request):
    big_text = "X" * 1000000
    return {"data": big_text}

@app.route("/compute")
async def compute(request: Request):
    # simple CPU-bound Fibonacci
    def fib(n: int) -> int:
        if n <= 1:
            return n
        return fib(n - 1) + fib(n - 2)
    return {"fib": fib(20)}

@app.route("/sleep")
async def sleep(request: Request):
    secs = float(request.query_params.get("secs", 0.1))
    await asyncio.sleep(secs)
    return {"slept": secs}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)

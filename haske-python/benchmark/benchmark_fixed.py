import asyncio
import httpx
import time
import statistics

# Frameworks da endpoints
FRAMEWORKS = {
    "Haske": "http://127.0.0.1:8000",
    "FastAPI": "http://127.0.0.1:8001"
}

ENDPOINTS = [
    "/json",
    "/query?name=ChatGPT",
    "/headers",
    "/post_small",
    "/post_large",
    "/large_resp",
    "/compute",
    "/sleep?secs=0.1"
]

# Settings
CONCURRENCY = 250
REQUESTS = 1000   # Jimillar requests per endpoint


async def fetch(client, url, results):
    start = time.perf_counter()
    try:
        resp = await client.get(url, timeout=10.0)
        latency = (time.perf_counter() - start) * 1000
        results.append(("ok", latency))
    except Exception:
        latency = (time.perf_counter() - start) * 1000
        results.append(("err", latency))


async def run_benchmark(name, base_url):
    print(f"\n🚀 Benchmarking {name} ...")
    data = {}

    async with httpx.AsyncClient() as client:
        for endpoint in ENDPOINTS:
            url = base_url + endpoint
            results = []

            start_time = time.perf_counter()

            tasks = [fetch(client, url, results) for _ in range(REQUESTS)]
            for i in range(0, len(tasks), CONCURRENCY):
                await asyncio.gather(*tasks[i:i+CONCURRENCY])

            duration = time.perf_counter() - start_time

            latencies = [r[1] for r in results if r[0] == "ok"]
            errors = sum(1 for r in results if r[0] == "err")
            total = len(results)

            if latencies:
                rps = total / duration
                avg = statistics.mean(latencies)
                p50 = statistics.median(latencies)
                latencies.sort()
                p90 = latencies[int(0.9 * len(latencies)) - 1]
                p95 = latencies[int(0.95 * len(latencies)) - 1]
                p99 = latencies[int(0.99 * len(latencies)) - 1]
            else:
                rps = avg = p50 = p90 = p95 = p99 = 0

            data[endpoint] = {
                "RPS": round(rps, 2),
                "Avg": round(avg, 2),
                "p50": round(p50, 2),
                "p90": round(p90, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "Errors": errors
            }

    return data


def print_table(framework, results):
    print("="*100)
    print(f"Framework: {framework}")
    print(f"{'Endpoint':<20} {'RPS':<8} {'Avg(ms)':<10} {'p50':<8} {'p90':<8} {'p95':<8} {'p99':<8} {'Errors':<8}")
    print("-"*100)
    for ep, s in results.items():
        print(f"{ep:<20} {s['RPS']:<8} {s['Avg']:<10} {s['p50']:<8} {s['p90']:<8} {s['p95']:<8} {s['p99']:<8} {s['Errors']:<8}")
    print("="*100)


async def main():
    for fw, url in FRAMEWORKS.items():
        res = await run_benchmark(fw, url)
        print_table(fw, res)


if __name__ == "__main__":
    asyncio.run(main())

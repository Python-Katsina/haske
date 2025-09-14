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
CONCURRENCY = 50   # max concurrent requests
REQUESTS = 1000      # total requests per endpoint
SEMAPHORE = asyncio.Semaphore(CONCURRENCY)


async def fetch(client, url, results):
    async with SEMAPHORE:
        start = time.perf_counter()
        try:
            resp = await client.get(url, timeout=50.0)
            latency = time.perf_counter() - start
            results.append(("ok", latency))
        except Exception:
            latency = time.perf_counter() - start
            results.append(("err", latency))


async def run_benchmark(name, base_url):
    print(f"\n🚀 Benchmarking {name} ...")
    data = {}

    limits = httpx.Limits(
        max_connections=CONCURRENCY,
        max_keepalive_connections=CONCURRENCY
    )

    async with httpx.AsyncClient(limits=limits) as client:
        for endpoint in ENDPOINTS:
            url = base_url + endpoint
            results = []

            start_time = time.perf_counter()

            tasks = [fetch(client, url, results) for _ in range(REQUESTS)]
            await asyncio.gather(*tasks)

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

                min_latency = min(latencies)
                max_latency = max(latencies)
                stdev = statistics.pstdev(latencies)
            else:
                rps = avg = p50 = p90 = p95 = p99 = 0
                min_latency = max_latency = stdev = 0

            data[endpoint] = {
                "RPS": round(rps, 2),
                "Avg": round(avg, 4),
                "p50": round(p50, 4),
                "p90": round(p90, 4),
                "p95": round(p95, 4),
                "p99": round(p99, 4),
                "Min": round(min_latency, 4),
                "Max": round(max_latency, 4),
                "Stdev": round(stdev, 4),
                "Errors": errors,
                "Duration": round(duration, 2)
            }

    return data


def print_table(framework, results):
    print("=" * 140)
    print(f"Framework: {framework}")
    print(f"{'Endpoint':<20} {'RPS':<8} {'Avg(s)':<10} {'p50':<8} {'p90':<8} "
          f"{'p95':<8} {'p99':<8} {'Min':<8} {'Max':<8} {'Stdev':<10} {'Errors':<8} {'Dur(s)':<8}")
    print("-" * 140)
    for ep, s in results.items():
        print(f"{ep:<20} {s['RPS']:<8} {s['Avg']:<10} {s['p50']:<8} {s['p90']:<8} "
              f"{s['p95']:<8} {s['p99']:<8} {s['Min']:<8} {s['Max']:<8} "
              f"{s['Stdev']:<10} {s['Errors']:<8} {s['Duration']:<8}")
    print("=" * 140)


async def main():
    for fw, url in FRAMEWORKS.items():
        res = await run_benchmark(fw, url)
        print_table(fw, res)


if __name__ == "__main__":
    asyncio.run(main())

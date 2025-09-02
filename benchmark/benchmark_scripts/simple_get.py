# benchmarks/benchmark_scripts/simple_get.py
import httpx
import time
import asyncio
import statistics

async def benchmark_simple_get(url: str, num_requests: int = 1000):
    async with httpx.AsyncClient() as client:
        times = []
        
        for i in range(num_requests):
            start_time = time.time()
            response = await client.get(url)
            end_time = time.time()
            
            if response.status_code == 200:
                times.append((end_time - start_time) * 1000)  # Convert to ms
        
        return {
            "total_requests": num_requests,
            "successful_requests": len(times),
            "avg_response_time": statistics.mean(times),
            "min_response_time": min(times),
            "max_response_time": max(times),
            "p95": statistics.quantiles(times, n=20)[18],  # 95th percentile
            "requests_per_second": len(times) / (max(times) / 1000) if times else 0
        }

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/"
    result = asyncio.run(benchmark_simple_get(url, 1000))
    print(result)
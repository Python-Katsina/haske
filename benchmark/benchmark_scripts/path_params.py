# benchmarks/benchmark_scripts/path_params.py
import httpx
import time
import asyncio
import statistics
import random

async def benchmark_path_params(base_url: str, num_requests: int = 1000):
    async with httpx.AsyncClient() as client:
        times = []
        
        for i in range(num_requests):
            user_id = random.randint(1, 1000)
            start_time = time.time()
            response = await client.get(f"{base_url}/{user_id}")
            end_time = time.time()
            
            if response.status_code == 200:
                times.append((end_time - start_time) * 1000)
        
        return {
            "total_requests": num_requests,
            "successful_requests": len(times),
            "avg_response_time": statistics.mean(times),
            "min_response_time": min(times),
            "max_response_time": max(times),
            "p95": statistics.quantiles(times, n=20)[18],
            "requests_per_second": len(times) / (max(times) / 1000) if times else 0
        }
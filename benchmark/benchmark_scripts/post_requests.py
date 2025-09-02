# benchmarks/benchmark_scripts/post_requests.py (updated)
import httpx
import time
import asyncio
import statistics
import json
import random

async def benchmark_post_requests(url: str, num_requests: int = 1000):
    async with httpx.AsyncClient() as client:
        times = []
        successful = 0
        
        # Test data for POST requests
        test_users = [
            {"name": f"User {i}", "email": f"user{i}@example.com", "age": random.randint(18, 65)}
            for i in range(num_requests)
        ]
        
        for i in range(num_requests):
            user_data = test_users[i]
            start_time = time.time()
            try:
                response = await client.post(
                    url,
                    json=user_data,
                    headers={"Content-Type": "application/json"}
                )
                end_time = time.time()
                
                if response.status_code in [200, 201]:
                    times.append((end_time - start_time) * 1000)
                    successful += 1
            except Exception as e:
                end_time = time.time()
                print(f"Request {i} failed: {e}")
        
        return {
            "total_requests": num_requests,
            "successful_requests": successful,
            "avg_response_time": statistics.mean(times) if times else 0,
            "min_response_time": min(times) if times else 0,
            "max_response_time": max(times) if times else 0,
            "p95": statistics.quantiles(times, n=20)[18] if len(times) > 20 else (times[-1] if times else 0),
            "requests_per_second": successful / (max(times) / 1000) if times and max(times) > 0 else 0
        }

async def benchmark_post_form_data(url: str, num_requests: int = 1000):
    async with httpx.AsyncClient() as client:
        times = []
        successful = 0
        
        for i in range(num_requests):
            form_data = {
                "name": f"Test User {i}",
                "email": f"test{i}@example.com",
                "message": f"This is test message number {i} for benchmarking form submissions"
            }
            
            start_time = time.time()
            try:
                response = await client.post(
                    url,
                    data=form_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                end_time = time.time()
                
                if response.status_code in [200, 201]:
                    times.append((end_time - start_time) * 1000)
                    successful += 1
            except Exception as e:
                end_time = time.time()
                print(f"Request {i} failed: {e}")
        
        return {
            "total_requests": num_requests,
            "successful_requests": successful,
            "avg_response_time": statistics.mean(times) if times else 0,
            "min_response_time": min(times) if times else 0,
            "max_response_time": max(times) if times else 0,
            "p95": statistics.quantiles(times, n=20)[18] if len(times) > 20 else (times[-1] if times else 0),
            "requests_per_second": successful / (max(times) / 1000) if times and max(times) > 0 else 0
        }

# ... rest of the file remains the same
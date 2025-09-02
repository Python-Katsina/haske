# benchmarks/benchmark_scripts/template_rendering.py
import httpx
import time
import asyncio
import statistics
from bs4 import BeautifulSoup

async def benchmark_template_rendering(url: str, num_requests: int = 1000):
    async with httpx.AsyncClient() as client:
        times = []
        content_lengths = []
        
        for i in range(num_requests):
            start_time = time.time()
            response = await client.get(url)
            end_time = time.time()
            
            if response.status_code == 200:
                times.append((end_time - start_time) * 1000)  # Convert to ms
                content_lengths.append(len(response.content))
                
                # Verify it's actually HTML (optional)
                if i % 100 == 0:  # Check every 100th request to avoid overhead
                    soup = BeautifulSoup(response.text, 'html.parser')
                    if not soup.find():
                        print(f"Warning: Response may not be HTML at request {i}")
        
        return {
            "total_requests": num_requests,
            "successful_requests": len(times),
            "avg_response_time": statistics.mean(times) if times else 0,
            "min_response_time": min(times) if times else 0,
            "max_response_time": max(times) if times else 0,
            "p95": statistics.quantiles(times, n=20)[18] if len(times) > 20 else (times[-1] if times else 0),
            "requests_per_second": len(times) / (max(times) / 1000) if times and max(times) > 0 else 0,
            "avg_content_length": statistics.mean(content_lengths) if content_lengths else 0,
            "min_content_length": min(content_lengths) if content_lengths else 0,
            "max_content_length": max(content_lengths) if content_lengths else 0
        }

async def benchmark_complex_template(url: str, num_requests: int = 500):
    """Benchmark with more complex template operations"""
    async with httpx.AsyncClient() as client:
        times = []
        
        for i in range(num_requests):
            start_time = time.perf_counter()  # More precise timing
            response = await client.get(url)
            end_time = time.perf_counter()
            
            if response.status_code == 200:
                times.append((end_time - start_time) * 1000)
        
        return {
            "total_requests": num_requests,
            "successful_requests": len(times),
            "avg_response_time": statistics.mean(times) if times else 0,
            "min_response_time": min(times) if times else 0,
            "max_response_time": max(times) if times else 0,
            "p95": statistics.quantiles(times, n=20)[18] if len(times) > 20 else (times[-1] if times else 0),
            "requests_per_second": len(times) / (max(times) / 1000) if times and max(times) > 0 else 0
        }

async def benchmark_template_with_variables(base_url: str, num_requests: int = 1000):
    """Benchmark templates with different variables"""
    async with httpx.AsyncClient() as client:
        times = []
        
        for i in range(num_requests):
            # Use different query parameters to test variable passing
            url_with_params = f"{base_url}?count={i % 50}&name=TestUser{i}"
            start_time = time.time()
            response = await client.get(url_with_params)
            end_time = time.time()
            
            if response.status_code == 200:
                times.append((end_time - start_time) * 1000)
        
        return {
            "total_requests": num_requests,
            "successful_requests": len(times),
            "avg_response_time": statistics.mean(times) if times else 0,
            "min_response_time": min(times) if times else 0,
            "max_response_time": max(times) if times else 0,
            "p95": statistics.quantiles(times, n=20)[18] if len(times) > 20 else (times[-1] if times else 0),
            "requests_per_second": len(times) / (max(times) / 1000) if times and max(times) > 0 else 0
        }

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/template"
    
    print("Testing template rendering...")
    result = asyncio.run(benchmark_template_rendering(url, 1000))
    print("Template Rendering Results:", result)
    
    print("\nTesting template with variables...")
    result_vars = asyncio.run(benchmark_template_with_variables(url, 1000))
    print("Template with Variables Results:", result_vars)
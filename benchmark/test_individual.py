# benchmarks/test_individual.py
import asyncio
import sys
from benchmark_scripts.post_requests import benchmark_post_requests, benchmark_post_form_data, benchmark_post_large_payload
from benchmark_scripts.template_rendering import benchmark_template_rendering, benchmark_template_with_variables

async def test_endpoint(url: str, test_type: str, num_requests: int = 1000):
    """Test a specific endpoint"""
    if test_type == "post_json":
        return await benchmark_post_requests(url, num_requests)
    elif test_type == "post_form":
        return await benchmark_post_form_data(url, num_requests)
    elif test_type == "post_large":
        return await benchmark_post_large_payload(url, min(num_requests, 10000))
    elif test_type == "template":
        return await benchmark_template_rendering(url, num_requests)
    elif test_type == "template_vars":
        return await benchmark_template_with_variables(url, num_requests)
    else:
        raise ValueError(f"Unknown test type: {test_type}")

async def main():
    if len(sys.argv) < 3:
        print("Usage: python test_individual.py <url> <test_type> [num_requests]")
        print("Test types: post_json, post_form, post_large, template, template_vars")
        return
    
    url = sys.argv[1]
    test_type = sys.argv[2]
    num_requests = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    
    print(f"Testing {test_type} at {url} with {num_requests} requests...")
    
    result = await test_endpoint(url, test_type, num_requests)
    print("Results:", result)

if __name__ == "__main__":
    asyncio.run(main())
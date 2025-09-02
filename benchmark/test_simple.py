# benchmarks/test_simple.py
import httpx
import asyncio

async def test_simple():
    """Test basic endpoints to ensure they work"""
    servers = {
        "haske": "http://localhost:8000",
        "fastapi": "http://localhost:8001"
    }
    
    for name, url in servers.items():
        print(f"\nTesting {name} server at {url}")
        print("-" * 40)
        
        async with httpx.AsyncClient() as client:
            # Test simple GET
            try:
                response = await client.get(f"{url}/", timeout=5.0)
                print(f"GET / -> {response.status_code}")
                if response.status_code == 200:
                    print(f"Response: {response.json()}")
            except Exception as e:
                print(f"GET / failed: {e}")
            
            # Test JSON endpoint
            try:
                response = await client.get(f"{url}/json", timeout=5.0)
                print(f"GET /json -> {response.status_code}")
            except Exception as e:
                print(f"GET /json failed: {e}")
            
            # Test path parameters
            try:
                response = await client.get(f"{url}/users/123", timeout=5.0)
                print(f"GET /users/123 -> {response.status_code}")
            except Exception as e:
                print(f"GET /users/123 failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple())
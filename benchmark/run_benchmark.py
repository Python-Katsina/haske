# benchmarks/run_benchmarks.py
import asyncio
import json
import time
import subprocess
import sys
from pathlib import Path
import httpx
from benchmark_scripts.simple_get import benchmark_simple_get
from benchmark_scripts.json_response import benchmark_json_response
from benchmark_scripts.path_params import benchmark_path_params
from benchmark_scripts.post_requests import benchmark_post_requests, benchmark_post_form_data
from benchmark_scripts.template_rendering import benchmark_template_rendering

async def check_server_ready(url: str, timeout: int = 30):
    """Check if server is ready to accept requests"""
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(url, timeout=2.0)
                if response.status_code == 200:
                    print(f"✅ Server is ready at {url}")
                    return True
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
                await asyncio.sleep(1)
                print("⏳ Waiting for server to start...")
        return False

async def run_benchmarks(framework: str, port: int):
    base_url = f"http://localhost:{port}"
    results = {}
    
    print(f"🚀 Benchmarking {framework}...")
    
    # Check if server is ready
    if not await check_server_ready(f"{base_url}/"):
        print(f"❌ Server {framework} failed to start")
        return None
    
    try:
        # Test 1: Simple GET
        print("📊 Testing Simple GET...")
        results['simple_get'] = await benchmark_simple_get(f"{base_url}/", 1000)
        
        # Test 2: JSON Response
        print("📊 Testing JSON Response...")
        results['json_response'] = await benchmark_json_response(f"{base_url}/json", 1000)
        
        # Test 3: Path Parameters
        print("📊 Testing Path Parameters...")
        results['path_params'] = await benchmark_path_params(f"{base_url}/users", 1000)
        
        # Test 4: POST Requests - JSON
        print("📊 Testing POST Requests (JSON)...")
        results['post_json'] = await benchmark_post_requests(f"{base_url}/users", 500)
        
        # Test 5: Template Rendering
        print("📊 Testing Template Rendering...")
        results['template_rendering'] = await benchmark_template_rendering(f"{base_url}/template", 500)
        
        # Test 6: CPU Intensive
        print("📊 Testing CPU Intensive Task...")
        results['cpu_intensive'] = await benchmark_simple_get(f"{base_url}/fib/20", 50)
        
        return results
        
    except Exception as e:
        print(f"❌ Error during benchmarking {framework}: {e}")
        import traceback
        traceback.print_exc()
        return None

def start_server(framework: str, port: int):
    """Start the server in a subprocess"""
    if framework == "haske":
        cmd = [sys.executable, "haske_app.py"]
    else:
        cmd = ["uvicorn", "fastapi_app:app", "--port", str(port), "--host", "0.0.0.0"]
    
    print(f"🔄 Starting {framework} server: {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

async def main():
    frameworks = ["haske", "fastapi"]
    ports = {"haske": 8000, "fastapi": 8001}
    all_results = {}
    
    # Create results directory
    Path("results").mkdir(exist_ok=True)
    
    for framework in frameworks:
        # Start server
        print(f"\n{'='*50}")
        print(f"🔄 Starting {framework} server...")
        server_process = start_server(framework, ports[framework])
        
        # Wait a moment for server to start
        await asyncio.sleep(2)
        
        try:
            # Run benchmarks
            results = await run_benchmarks(framework, ports[framework])
            
            if results:
                all_results[framework] = results
                
                # Save results
                with open(f"results/{framework}_results.json", "w") as f:
                    json.dump(results, f, indent=2)
                    
                print(f"✅ {framework} benchmarking completed!")
                print(f"📊 Results saved to results/{framework}_results.json")
                
                # Display summary
                print("\n📈 Summary:")
                for test_name, result in results.items():
                    rps = result.get('requests_per_second', 0)
                    print(f"  {test_name}: {rps:.2f} RPS")
                    
            else:
                print(f"❌ {framework} benchmarking failed")
                
        except Exception as e:
            print(f"❌ Error with {framework}: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Stop server
            if server_process:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_process.kill()
                print(f"🛑 {framework} server stopped")
    
    # Generate comparison report if we have results
    if all_results:
        generate_report(all_results)
    else:
        print("❌ No benchmark results were collected")

def generate_report(results):
    """Generate a comparison report"""
    report = {
        "summary": {},
        "detailed": results,
        "timestamp": time.time()
    }
    
    for test_name in ["simple_get", "json_response", "path_params", "post_json", "template_rendering", "cpu_intensive"]:
        if test_name in results.get("haske", {}) and test_name in results.get("fastapi", {}):
            haske_rps = results["haske"][test_name].get("requests_per_second", 0)
            fastapi_rps = results["fastapi"][test_name].get("requests_per_second", 0)
            
            report["summary"][test_name] = {
                "haske_rps": round(haske_rps, 2),
                "fastapi_rps": round(fastapi_rps, 2),
                "difference": round(haske_rps - fastapi_rps, 2),
                "percentage_diff": round(((haske_rps - fastapi_rps) / fastapi_rps) * 100, 2) if fastapi_rps > 0 else 0,
                "winner": "Haske" if haske_rps > fastapi_rps else "FastAPI"
            }
    
    # Calculate overall performance
    haske_total_rps = sum([results["haske"][test].get("requests_per_second", 0) for test in report["summary"]])
    fastapi_total_rps = sum([results["fastapi"][test].get("requests_per_second", 0) for test in report["summary"]])
    
    report["overall"] = {
        "haske_total_rps": round(haske_total_rps, 2),
        "fastapi_total_rps": round(fastapi_total_rps, 2),
        "overall_difference": round(haske_total_rps - fastapi_total_rps, 2),
        "overall_percentage": round(((haske_total_rps - fastapi_total_rps) / fastapi_total_rps) * 100, 2) if fastapi_total_rps > 0 else 0,
        "overall_winner": "Haske" if haske_total_rps > fastapi_total_rps else "FastAPI"
    }
    
    with open("results/comparison_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*50}")
    print("📈 FINAL BENCHMARK RESULTS")
    print("=" * 50)
    
    for test_name, data in report["summary"].items():
        print(f"{test_name:20} | Haske: {data['haske_rps']:6.1f} RPS | FastAPI: {data['fastapi_rps']:6.1f} RPS | Winner: {data['winner']}")
    
    print("-" * 50)
    print(f"{'OVERALL':20} | Haske: {report['overall']['haske_total_rps']:6.1f} RPS | FastAPI: {report['overall']['fastapi_total_rps']:6.1f} RPS | Winner: {report['overall']['overall_winner']}")
    print(f"Performance difference: {report['overall']['overall_percentage']:+.1f}%")
    
    print(f"\n📊 Detailed results saved to results/comparison_report.json")

if __name__ == "__main__":
    print("🚀 Starting Haske vs FastAPI Benchmark")
    print("=" * 50)
    asyncio.run(main())
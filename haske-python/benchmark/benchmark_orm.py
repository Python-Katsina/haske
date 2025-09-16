import asyncio
import time
import httpx
import statistics
import argparse
import json
import csv
from collections import Counter

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    USE_RICH = True
except ImportError:
    console = None
    USE_RICH = False


async def worker(client, url, tasks_per_worker, timeout, results):
    for _ in range(tasks_per_worker):
        start = time.perf_counter()
        try:
            resp = await client.get(url, timeout=timeout)
            latency = time.perf_counter() - start
            results.append((resp.status_code, latency))
        except Exception as e:
            results.append(("error", None))


async def run_benchmark(url, total_requests, concurrency, timeout, warmup=5):
    results = []

    async with httpx.AsyncClient() as client:
        # warmup
        for _ in range(warmup):
            try:
                await client.get(url, timeout=timeout)
            except Exception:
                pass

        tasks = []
        tasks_per_worker = total_requests // concurrency
        for _ in range(concurrency):
            tasks.append(worker(client, url, tasks_per_worker, timeout, results))

        start = time.perf_counter()
        await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

    # --- results ---
    success = sum(1 for code, _ in results if code == 200)
    errors = sum(1 for code, _ in results if code != 200)
    latencies = [lat for _, lat in results if lat is not None]
    error_breakdown = Counter(str(code) for code, _ in results if code != 200)

    stats = {
        "url": url,
        "total_requests": total_requests,
        "concurrency": concurrency,
        "success": success,
        "errors": errors,
        "error_breakdown": dict(error_breakdown),
        "total_time": duration,
        "req_per_sec": total_requests / duration if duration > 0 else 0,
        "latency_avg": statistics.mean(latencies) if latencies else None,
        "latency_min": min(latencies) if latencies else None,
        "latency_max": max(latencies) if latencies else None,
        "latency_p50": statistics.quantiles(latencies, n=100)[49] if latencies else None,
        "latency_p75": statistics.quantiles(latencies, n=100)[74] if latencies else None,
        "latency_p90": statistics.quantiles(latencies, n=100)[89] if latencies else None,
        "latency_p95": statistics.quantiles(latencies, n=100)[94] if latencies else None,
        "latency_p99": statistics.quantiles(latencies, n=100)[98] if latencies else None,
    }

    return stats


def print_results(stats):
    if USE_RICH:
        table = Table(title="Benchmark Results")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        for key, label in [
            ("url", "Target URL"),
            ("total_requests", "Total Requests"),
            ("concurrency", "Concurrency"),
            ("success", "Success"),
            ("errors", "Errors"),
            ("total_time", "Total Time (s)"),
            ("req_per_sec", "Requests/sec"),
            ("latency_avg", "Avg Latency (s)"),
            ("latency_min", "Min Latency (s)"),
            ("latency_max", "Max Latency (s)"),
            ("latency_p50", "P50 Latency (s)"),
            ("latency_p75", "P75 Latency (s)"),
            ("latency_p90", "P90 Latency (s)"),
            ("latency_p95", "P95 Latency (s)"),
            ("latency_p99", "P99 Latency (s)"),
        ]:
            val = stats.get(key)
            if isinstance(val, float):
                val = f"{val:.4f}"
            table.add_row(label, str(val))
        console.print(table)

        if stats["error_breakdown"]:
            console.print("[bold red]Error Breakdown:[/bold red]")
            for code, count in stats["error_breakdown"].items():
                console.print(f"  {code}: {count}")
    else:
        print("=== Benchmark Results ===")
        for k, v in stats.items():
            print(f"{k}: {v}")


def export_results(stats, fmt, filename):
    if fmt == "json":
        with open(filename, "w") as f:
            json.dump(stats, f, indent=2)
    elif fmt == "csv":
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(stats.keys())
            writer.writerow(stats.values())


def main():
    parser = argparse.ArgumentParser(description="HTTP Benchmark Tool")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8000/users/1", help="Target URL")
    parser.add_argument("--requests", type=int, default=1000, help="Total requests")
    parser.add_argument("--concurrency", type=int, default=500, help="Concurrent workers")
    parser.add_argument("--timeout", type=float, default=50.0, help="Request timeout in seconds")
    parser.add_argument("--export", type=str, choices=["json", "csv"], help="Export format")
    parser.add_argument("--output", type=str, help="Output file name")

    args = parser.parse_args()

    stats = asyncio.run(
        run_benchmark(args.url, args.requests, args.concurrency, args.timeout)
    )
    print_results(stats)

    if args.export and args.output:
        export_results(stats, args.export, args.output)
        print(f"Results exported to {args.output}")


if __name__ == "__main__":
    main()

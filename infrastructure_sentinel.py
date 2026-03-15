"""
Infrastructure Response Sentinel v2.0 - Professional Edition
High-performance server health monitor with concurrent workers and Rich TUI.

refactor: optimize async I/O and connection pooling
- Migrated to a single shared aiohttp.ClientSession to prevent connection pool exhaustion.
- Implemented asyncio.Queue and aiofiles for non-blocking, thread-safe JSON logging.
- Eliminated synchronous I/O operations from the main event loop to ensure high-performance concurrent probing.
"""

import asyncio
import aiohttp
from aiohttp import ClientTimeout
import time
import json
import sys
import argparse
from datetime import datetime
from rich.live import Live
from rich.table import Table
from rich.console import Console
import aiofiles
from rich.layout import Layout
from rich.panel import Panel

class Statistics:
    def __init__(self):
        self.total_requests = 0
        self.success_count = 0
        self.error_count = 0
        self.latencies = []
        self.start_time = time.time()
        self.active_conns = 0
        self.last_status = "N/A"
        self._lock = asyncio.Lock()

    @property
    def avg_latency(self):
        if not self.latencies: return 0
        return sum(self.latencies) / len(self.latencies)

    @property
    def error_rate(self):
        if self.total_requests == 0: return 0
        return (self.error_count / self.total_requests) * 100

    async def add_result(self, latency, success, status):
        async with self._lock:
            self.total_requests += 1
            self.last_status = str(status)
            if success:
                self.success_count += 1
                self.latencies.append(latency)
                if len(self.latencies) > 100:
                    self.latencies.pop(0)
            else:
                self.error_count += 1

    def to_dict(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "total_reqs": self.total_requests,
            "success": self.success_count,
            "errors": self.error_count,
            "error_rate_pct": round(self.error_rate, 2),
            "avg_latency_ms": round(self.avg_latency * 1000, 2),
            "active_conns": self.active_conns,
            "last_status": self.last_status
        }

async def logger_worker(queue, output_file):
    async with aiofiles.open(output_file, mode='a') as f:
        while True:
            log_entry = await queue.get()
            if log_entry is None:  # Sentinel value to stop logger
                break
            await f.write(json.dumps(log_entry) + "\n")
            await f.flush()
            queue.task_done()

async def worker(url, session, stats, interval, timeout, log_queue=None):
    while True:
        async with stats._lock:
            stats.active_conns += 1
        
        t0 = time.time()
        try:
            async with session.get(url, timeout=ClientTimeout(total=timeout)) as response:
                t1 = time.time()
                latency = t1 - t0
                success = 200 <= response.status < 400
                await stats.add_result(latency, success, response.status)
        except Exception as e:
            await stats.add_result(0, False, "ERR")
        finally:
            async with stats._lock:
                stats.active_conns -= 1

        if log_queue:
            await log_queue.put(stats.to_dict())

        await asyncio.sleep(interval)

def generate_table(stats, url) -> Table:
    data = stats.to_dict()
    table = Table(title=f"Sentinel v2.0 - Monitoring: [bold cyan]{url}[/]", border_style="bright_blue")
    
    table.add_column("Metric", style="bold yellow")
    table.add_column("Value", justify="right")
    
    table.add_row("Timestamp", data['timestamp'].split('.')[0].replace('T', ' '))
    table.add_row("Total Requests", str(data['total_reqs']))
    table.add_row("Success Count", f"[green]{data['success']}[/]")
    table.add_row("Error Count", f"[red]{data['errors']}[/]")
    table.add_row("Error Rate", f"{data['error_rate_pct']}%")
    table.add_row("Avg Latency", f"[bold white]{data['avg_latency_ms']} ms[/]")
    table.add_row("Active Connections", f"[bold magenta]{data['active_conns']}[/]")
    table.add_row("Last Status", f"[bold]{data['last_status']}[/]")
    
    return table

async def main():
    parser = argparse.ArgumentParser(description="Infrastructure Response Sentinel v2.0")
    parser.add_argument("url", help="Target URL to monitor")
    parser.add_argument("--rate", type=float, default=0.5, help="Probing interval per worker (seconds)")
    parser.add_argument("--workers", type=int, default=5, help="Number of concurrent workers (default: 5)")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout (seconds)")
    parser.add_argument("--output", help="Path to save JSON log stream")
    args = parser.parse_args()

    stats = Statistics()
    console = Console()
    
    log_queue = asyncio.Queue() if args.output else None
    
    async with aiohttp.ClientSession() as session:
        # 1. Cria a lista SÓ com os workers e a UI
        worker_tasks = [asyncio.create_task(worker(args.url, session, stats, args.rate, args.timeout, log_queue)) 
                 for _ in range(args.workers)]
        
        logger_task = None
        if log_queue:
            # 2. Guarda o logger isolado
            logger_task = asyncio.create_task(logger_worker(log_queue, args.output))

        try:
            with Live(generate_table(stats, args.url), refresh_per_second=4, console=console) as live:
                # We run workers and a simple UI updater
                async def update_ui():
                    while True:
                        live.update(generate_table(stats, args.url))
                        await asyncio.sleep(0.25)
                
                worker_tasks.append(asyncio.create_task(update_ui()))
                
                # Executa apenas os workers e UI no gather principal
                await asyncio.gather(*worker_tasks)
                
        except KeyboardInterrupt:
            console.print("\n[bold red][!] Sentinel stopped by user. Shutting down gracefully...[/]")
            
            # 1. Cancela apenas os workers e a UI (Eles param de gerar novos dados)
            for task in worker_tasks:
                task.cancel()
            
            # 2. Avisa o logger que acabou e ESPERA ele esvaziar a fila e fechar o arquivo
            if log_queue and logger_task:
                log_queue.put_nowait(None)
                await logger_task 
            
            # 3. Limpa o cancelamento dos workers
            await asyncio.gather(*worker_tasks, return_exceptions=True)
            
        except Exception as e:
            console.print(f"\n[bold red][!] Fatal error: {e}[/]")
            sys.exit(1)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

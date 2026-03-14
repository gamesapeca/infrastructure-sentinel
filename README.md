# Infrastructure Response Sentinel v2.0

![Sentinel Dashboard](https://raw.githubusercontent.com/your-username/infrastructure-sentinel/main/preview.png)

A high-performance, asynchronous server health monitor designed for stress-testing and infrastructure resilience analysis. Built with Python, `asyncio`, and `Rich`.

## 🚀 Features

- **Concurrent Worker Pool**: Simulate multiple simultaneous probes to measure real-world connection limits.
- **Real-time TUI**: A professional, dynamic terminal dashboard for instant metrics visualization.
- **Precision Metrics**: Tracking average latency (RTT), success/error rates, and active connections.
- **JSON Logging**: Continuous data streaming to JSON for time-series analysis and post-test reporting.
- **Thread-safe Engine**: Implements async locks to ensure data integrity during high-throughput monitoring.

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/infrastructure-sentinel.git
   cd infrastructure-sentinel
   ```

2. Install dependencies:
   ```bash
   pip install aiohttp rich
   ```

## 📖 Usage

Run the sentinel against any target endpoint:

```bash
python infrastructure_sentinel.py https://api.yoursite.com --workers 10 --rate 0.1 --output results.json
```

### Options:
- `--workers`: Number of simultaneous probes (default: 5).
- `--rate`: Interval between probes per worker in seconds (default: 0.5).
- `--output`: Path to save the JSON log stream.

## 📊 Sample Output

The tool provides a clean, visual table in the terminal and a structured JSON log:

```json
{"timestamp": "2026-03-14T20:00:34", "total_reqs": 10, "success": 8, "errors": 2, "avg_latency_ms": 2332.97, "active_conns": 10}
```

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.

---
*Developed for infrastructure engineering and stress testing scenarios.*

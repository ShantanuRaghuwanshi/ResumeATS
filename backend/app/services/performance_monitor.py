import time
import asyncio
from contextlib import contextmanager
from typing import Dict, Any

class PerformanceMonitor:
    """
    Monitors performance metrics for service operations.
    """
    def __init__(self):
        self.metrics = {}
        self.operation_times = []
        self.active = False

    async def initialize(self):
        self.active = True
        self.metrics.clear()
        self.operation_times.clear()

    @contextmanager
    def track_operation(self, operation_name: str):
        start = time.time()
        try:
            yield
        finally:
            end = time.time()
            duration = end - start
            self.metrics.setdefault(operation_name, []).append(duration)
            self.operation_times.append(duration)

    async def get_stats(self) -> Dict[str, Any]:
        stats = {
            "total_operations": sum(len(v) for v in self.metrics.values()),
            "average_time": (sum(self.operation_times) / len(self.operation_times)) if self.operation_times else 0.0,
            "operation_metrics": {
                k: {
                    "count": len(v),
                    "avg_time": sum(v) / len(v) if v else 0.0,
                    "max_time": max(v) if v else 0.0,
                    "min_time": min(v) if v else 0.0,
                } for k, v in self.metrics.items()
            },
        }
        return stats

    async def shutdown(self):
        self.active = False
        self.metrics.clear()
        self.operation_times.clear()

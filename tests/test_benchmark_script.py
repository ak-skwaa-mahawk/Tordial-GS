import pytest
from scripts.benchmark_e8_throughput import benchmark_e8_dispatcher

def test_benchmark_execution():
    # Smoke test small iteration count
    benchmark_e8_dispatcher(iterations=50, batch_size=10)

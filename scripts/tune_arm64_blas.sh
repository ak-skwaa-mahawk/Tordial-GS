#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "⚙️  CONFIGURING OPENBLAS & SIMD PROFILING ON ARM64"
echo "=========================================================="

# Check CPU Cores
CPU_COUNT=$(nproc)
echo "[*] Detected CPU Cores: ${CPU_COUNT}"

# Inspect NumPy BLAS configuration
python -c "import numpy as np; np.show_config()"

echo ""
echo "=== BENCHMARKING THREAD POOL CONFIGURATIONS ==="

for THREADS in 1 2 4 8; do
    echo ""
    echo "--- Testing OPENBLAS_NUM_THREADS=${THREADS} ---"
    OPENBLAS_NUM_THREADS=${THREADS} \
    OMP_NUM_THREADS=${THREADS} \
    MKL_NUM_THREADS=${THREADS} \
    VECLIB_MAXIMUM_THREADS=${THREADS} \
    NUMEXPR_NUM_THREADS=${THREADS} \
    python scripts/benchmark_e8_throughput.py
done

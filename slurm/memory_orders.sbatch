#!/bin/bash -l
#SBATCH --job-name=n2-memory-orders
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PATH="$PWD/.env/bin:$PATH" PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg
mkdir -p results/memory-orders-v1
pytest -q tests/test_memory.py tests/test_memory_utc.py tests/test_memory_orders.py | tee results/memory-orders-v1/tests.txt
python src/memory_orders.py
sha256sum src/memory_orders.py src/memory_tools.py src/memory_utc_control.py src/n2tools.py tests/test_memory*.py slurm/memory_orders.sbatch docs/order_memory_approach.md > results/memory-orders-v1/source.sha256
cp results/memory-v1/data.sha256 results/memory-orders-v1/input-data.sha256

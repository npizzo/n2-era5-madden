#!/bin/bash -l
#SBATCH --job-name=n2-memory-validate
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PATH="$PWD/.env/bin:$PATH" PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg
mkdir -p results/memory-v1
pytest -q tests/test_memory.py | tee results/memory-v1/synthetic-tests.txt
python src/extract_memory_height.py --year 1979 --limit 200 --out data/memory-v1/pilot

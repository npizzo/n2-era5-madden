#!/bin/bash -l
#SBATCH --job-name=n2-memory-utc
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PATH="$PWD/.env/bin:$PATH" PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg
pytest -q tests/test_memory_utc.py | tee results/memory-v1/utc-tests.txt
python src/memory_utc_control.py
sha256sum src/memory_utc_control.py tests/test_memory_utc.py slurm/memory_utc.sbatch > results/memory-v1/utc-source.sha256

#!/bin/bash -l
#SBATCH --job-name=n2-memory-analysis
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PATH="$PWD/.env/bin:$PATH" PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg
mkdir -p results/memory-v1
pytest -q tests/test_memory.py | tee results/memory-v1/synthetic-tests.txt
python src/analyze_memory.py
sha256sum src/memory_tools.py src/extract_memory_height.py src/analyze_memory.py tests/test_memory.py slurm/memory_*.sbatch docs/memory_approach.md > results/memory-v1/source.sha256
find data/memory-v1 -type f -name '*.nc' -print0 | sort -z | xargs -0 sha256sum > results/memory-v1/data.sha256
mkdir -p archives
tar -czf archives/memory-v1-data.tar.gz data/memory-v1 results/memory-v1/data.sha256
sha256sum archives/memory-v1-data.tar.gz > results/memory-v1/archive.sha256

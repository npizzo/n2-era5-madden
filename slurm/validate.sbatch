#!/bin/bash -l
#SBATCH --job-name=n2-validate
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PATH="$PWD/.env/bin:$PATH" PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg
python -m pytest -q tests | tee results/synthetic-tests.txt
python src/check_data.py
python src/extract_wb2.py --year 1979 --limit 200 --out data/pilot

#!/bin/bash -l
#SBATCH --job-name=n2-extract
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --array=1979-2022%6
#SBATCH --output=logs/%x-%A_%a.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PATH="$PWD/.env/bin:$PATH" PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python src/extract_wb2.py --year "$SLURM_ARRAY_TASK_ID" --out data/stage1

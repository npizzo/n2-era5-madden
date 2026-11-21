#!/bin/bash -l
#SBATCH --job-name=n2-fine1979
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PATH="$PWD/.env/bin:$PATH" PYTHONPATH="$PWD/src"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python src/extract_wb2.py --year 1979 --lmax 89 --store gs://weatherbench2/datasets/era5/1959-2023_01_10-6h-360x181_equiangular_with_poles_conservative.zarr --out data/resolution1deg
python src/compare_resolution_year.py

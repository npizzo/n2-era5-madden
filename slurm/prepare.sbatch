#!/bin/bash -l
#SBATCH --job-name=n2-prepare
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
module load conda/latest
export CONDA_PKGS_DIRS="$PWD/.conda-pkgs"
conda env create --prefix "$PWD/.env" --file environment.yml -y
conda list --prefix "$PWD/.env" --explicit > results/environment-explicit.txt

#!/bin/bash -l
#SBATCH --job-name=n2-package-energy
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:15:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
mkdir -p archives
sha256sum data/energy/*.nc data/resolution1deg/*.nc data/pilot/*.nc > results/energy-data.sha256
test ! -e archives/energy-and-validation-data.tar.gz
tar -czf archives/energy-and-validation-data.tar.gz data/energy data/resolution1deg data/pilot results/energy-data.sha256
sha256sum archives/energy-and-validation-data.tar.gz > results/energy-archive.sha256

#!/bin/bash -l
#SBATCH --job-name=n2-package
#SBATCH --partition=uri-cpu,cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:15:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
mkdir -p archives
sha256sum data/stage1/coeffs_*.nc > results/coefficients.sha256
# Archive is a GitHub release asset, not a source commit.
test ! -e archives/stage1-coefficients-1979-2022.tar.gz
tar -czf archives/stage1-coefficients-1979-2022.tar.gz data/stage1 results/coefficients.sha256
sha256sum archives/stage1-coefficients-1979-2022.tar.gz > results/archive.sha256

# ERA5 n=2 energy — Madden validation on Unity

This project starts by checking large-scale Rossby-mode evidence against Madden (2007), using ERA5 300 and 500 hPa data for 1979–2022. It is an ERA5 comparison, not an exact reproduction of Madden's NCEP/NCAR analysis.

**Current status:** environment preparation and pilot validation submitted on Unity. No atmospheric result or Stage 1 pass is claimed yet. No Stage 2 computation is enabled.

## What is included

- Spherical-harmonic extraction with orientation, normalization, energy, and propagation-sign tests.
- A 1.5° versus 1° resolution comparison on ten dates.
- Two-sided spectra for five target modes, including seasonal and height comparisons.
- EOF loadings and all PC-pair coherence/phase diagnostics for zonal wavenumbers 1–4.
- Reproducible Unity job scripts and an explicit environment lock generated on the cluster.

Read [methods and differences from the plan](docs/methods.md) before interpreting a peak. The supplied [original plan](docs/original_plan.md) is retained for provenance.

## Run on Unity

Project directory: `/work/pi_nicholas_pizzo_uri_edu/n2-era5-madden`.

```bash
mkdir -p logs results data
sbatch slurm/prepare.sbatch
# After environment preparation succeeds:
sbatch slurm/validate.sbatch
# Review synthetic tests, data_checks.json and the 200-step pilot first.
extract_id=$(sbatch --parsable slurm/extract.sbatch)
sbatch --dependency=afterok:$extract_id slurm/analyze.sbatch
```

Compute tasks use Slurm, not the login node. The production array has six concurrent tasks, one per year. Completed coefficient files are protected against overwriting. To resume, submit only missing years rather than rerunning the entire array.

The scripts create `results/STAGE1_REPORT.md`, figures, `summary.json`, EOF/spectral arrays, and `data/stage1/coeffs_YYYY.nc`. Scientific interpretation remains a review step. Raw grids and credentials never enter this repository.

## Reference

[Madden (2007), Large-scale, free Rossby waves in the atmosphere—an update](https://doi.org/10.1111/j.1600-0870.2007.00257.x), Tellus A 59, 571–590.

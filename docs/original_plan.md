# Plan: n=2 spherical-harmonic energy in ERA5, run on Unity

Owners: Nick Pizzo & Rick Salmon. Executor: an AI assistant or person with a shell on Unity.
**Everything runs on Unity. Do not run anything on a laptop or another machine.**

Background and design rationale are in the shared doc *"n=2 energy in the atmosphere: ERA5 500 hPa workflow"*.
This file is the step-by-step execution plan. Starter code (`n2tools.py`, `transform.py`, `analyze.py`,
`run_transform.slurm`) was delivered separately. It passed synthetic tests only. Stage 1 below validates the
pipeline against Madden (2007) before any new science.

---

## 0. Science in one paragraph

Salmon & Pizzo (2023, *Atmosphere* 14, 747; 2024, *JFM* 996, A9) show that in 2D flow on a sphere, the n=1
modes are pinned by angular momentum. Energy therefore condenses into the five n=2 modes. Those modes, plus
the n=1 rotation, form a pattern that is rigid in a frame rotating at Ω − 2Ω/[n(n+1)] = 2Ω/3 (inertial).
Relative to Earth, that is 2ω/3 − Ω/3, where ω is the atmosphere's superrotation. We test whether ERA5 n=2
energy behaves this way:

- **H1:** spectrum
- **H2:** rigid shared pattern speed across m
- **H3:** longer memory in the comoving frame
- **H4:** nonlinear transfer into n=2

The relevance to intermediate-range forecasting comes after.

## 1. Conventions (use everywhere)

- Real 4π-normalized harmonics (pyshtools `norm=1`). The global mean of each basis function squared is 1.
- Complex amplitude: `a_n^m = C_nm − i S_nm`, so field = Σ Re[a_n^m e^{imλ}] P̄_nm.
- With that convention, a pattern moving at angular speed Ω_p (eastward positive) has `a ∝ e^{−imΩ_p t}`.
  Westward-moving waves therefore appear at **positive** numpy FFT frequency.
- To move to a comoving frame, multiply by `e^{+imΦ(t)}` with Φ = ∫Ω_p dt.
- Streamfunction: ψ_n^m = −a² ζ_n^m / [n(n+1)], with a = 6.371e6 m and Ω = 7.2921e-5 s⁻¹.
- KE per degree (global mean): E_n = ½ a²/[n(n+1)] Σ_m (C²+S²), summed over vorticity and divergence.
- Superrotation from the relative ζ₁⁰ coefficient: ω = (√3/2)·ζ₁⁰.
- Nondivergent Rossby–Haurwitz (RH) pattern speed, Earth frame: Ω_p = ω − 2(Ω+ω)/[n(n+1)].

## 2. Unity setup

1. **Storage** ([Unity storage docs](https://docs.unity.uri.edu/documentation/cluster_specs/storage)):
   - code and outputs: `/work/pi_<pi>/n2/` (1 TB, snapshotted)
   - any temporary grids: a `/scratch` workspace (no snapshots)
   - archived coefficient stores: `/project/pi_<pi>/n2/`
2. **Environment:**
   ```bash
   module avail conda            # confirm module name, e.g. conda/latest
   module load conda/latest
   conda create -n n2 -c conda-forge python=3.11 xarray zarr dask fsspec aiohttp gcsfs pyshtools \
         numpy scipy matplotlib netcdf4 -y
   conda activate n2
   ```
3. **Network check.** Run this on a compute node, not only the login node:
   ```bash
   srun -p cpu -c 1 --mem=2G -t 00:10:00 --pty bash
   python -c "import xarray as xr; ds=xr.open_zarr('gs://weatherbench2/datasets/era5/1959-2023_01_10-6h-240x121_equiangular_with_poles_conservative.zarr', storage_options={'token':'anon'}); print(ds.vorticity)"
   ```
   If compute nodes have no outbound internet, run the extraction (Stage 1a) from a login session in `tmux`,
   or from a data-transfer node if Unity has one. Everything after extraction is offline.
4. Check partition names with `sinfo`. The templates below use `-p cpu`.

## 3. Data source (no CDS key needed)

Use Google's public WeatherBench2 copy of ERA5 (zarr). Verified contents, Nov 2026:

| Store (prefix `gs://weatherbench2/datasets/era5/`) | Grid | Time | Levels (hPa) | Has `vorticity`, `divergence` | Chunks (time, level, lon, lat) |
|---|---|---|---|---|---|
| `1959-2023_01_10-6h-240x121_equiangular_with_poles_conservative.zarr` | 1.5°, poles incl. | 6-hourly, 1959-01-01 → 2023-01-10 | 50,100,150,200,250,300,400,500,600,700,850,925,1000 | yes | (8, 13, 240, 121) |
| `1959-2023_01_10-6h-360x181_equiangular_with_poles_conservative.zarr` | 1.0°, poles incl. | same | same | yes | (4, 13, 360, 181) |
| `1959-2022-1h-360x181_equiangular_with_poles_conservative.zarr` | 1.0° | hourly, to 2021-12-31 | 37 levels | **no** (u, v only) | (8, 37, 360, 181) |

Notes:
- Dims are ordered (time, level, longitude, latitude), and **latitude is ascending (−90 → 90)**. Before
  `pyshtools.expand.SHExpandDH`, transpose to (lat, lon), flip to 90 → −90, and drop the −90 row. That gives
  120×240 (1.5°, lmax ≤ 59) or 180×360 (1°, lmax ≤ 89), with `sampling=2`.
- Each chunk holds all 13 levels, so extract 300 and 500 hPa together; the cost is the same.
- Read speed measured from one stream elsewhere: about 200 steps in 7 s (1.5°) or 15 s (1°). Unity will
  differ. Parallelize across years with a job array.
- 6-hourly sampling puts the semidiurnal tide at Nyquist. That is fine for Stage 1, where periods are ≥ 2 days.
  For later frequency work near 1–2 cpd, use hourly data: the hourly zarr's u and v converted to vorticity
  spectrally, or the CDS.
- Alternative access: `https://storage.googleapis.com/weatherbench2/...` through fsspec HTTP.

## 4. Stage 1 — Validate against Madden (2007)

Madden (2007, *Tellus* 59A, 571–590) projected 40 years of reanalysis 300 hPa streamfunction onto spherical
harmonics and found the free (external) Rossby normal modes. Reproducing them checks the transforms, the
phase convention (westward = positive frequency), and the spectral method in one go.

### 1a. Extract coefficients (job array, one task per year, 1979–2022 = 44 tasks)

For each 6-hourly step at 300 and 500 hPa:
- `vorticity` → coefficients up to lmax=59 → keep complex `a_n^m` for n, m ≤ 21 (complex64).
- Also keep the rotational KE spectrum E_n (n ≤ 59) at both levels; it is cheap and needed for H1 later.

Save one file per year: `/work/pi_<pi>/n2/stage1/coeffs_YYYY.nc`, with dims (time, level, n, m) and
(time, level, nk). Total is about 0.5 GB.

```bash
#!/bin/bash
#SBATCH -J n2_extract
#SBATCH -p cpu -c 4 --mem=8G -t 02:00:00
#SBATCH --array=1979-2022%12
#SBATCH -o logs/%x_%a.out
module load conda/latest; conda activate n2
python extract_wb2.py --year $SLURM_ARRAY_TASK_ID --levels 300 500 --lmax 59 --keep 21 \
  --store gs://weatherbench2/datasets/era5/1959-2023_01_10-6h-240x121_equiangular_with_poles_conservative.zarr \
  --out /work/pi_<pi>/n2/stage1
```

`extract_wb2.py` should be adapted from `transform.py`:
- open the store with `xr.open_zarr(store, storage_options={'token':'anon'})`;
- select the year and levels, then `.load()` in blocks of about 200 steps;
- reorient the grid as described in §3;
- reuse `n2tools.grid_to_cilm`, `complex_coeffs` and `ke_spectrum`.

### 1b. Checks before any spectra

1. **Round trip:** synthesize → expand → compare. The error should be at machine precision (`test_n2tools.py`).
2. **Energy check:** global-mean KE from the grid equals Σ E_n to better than 1e-6 relative, for a few dates.
   Reconstruct u and v from ψ and χ using `divergence` too. Rotational-only KE will differ slightly from the
   full KE.
3. **Resolution check:** for about 10 dates, compare 1.5° and 1° coefficients (360x181 store) at n ≤ 21.
   Relative differences should be at most ~1%. Larger differences point to an orientation or normalization bug.
4. **Orientation check:** at 300 hPa in DJF, the time-mean ζ₁⁰ must be positive (westerly superrotation).
   Y₂⁰ should carry the hemispheric jet asymmetry with a clear annual cycle.

### 1c. Spectra

For each (s = m, l = n) pair below, use the 300 hPa streamfunction coefficient `a(t)`:
1. Remove the mean plus 4 annual harmonics, fitted by least squares (complex).
2. Compute a Welch spectrum of the complex series with 128-day Hann segments, 50% overlap, and dt = 6 h.
   Positive frequency means westward; negative means eastward.
3. Plot power vs period from 1.5 to 40 days, westward and eastward together. Overlay a heavily smoothed
   background (running median over ±25% in frequency) and its 95% χ² bound.
4. Repeat by season (DJF, JJA) and at 500 hPa.

### 1d. Expected results and pass criteria

Periods in days. Nondivergent RH = n(n+1)/(2m) sidereal days. Kasahara (1980) and Madden (2007) values are
taken from Madden (2007).

| Mode (s, l) | Name | Nondivergent RH | Divergent theory (Kasahara) | Observed (Madden) |
|---|---|---|---|---|
| (1, 2) | 5-day wave | 2.99 | 4.85 | ~5 |
| (1, 3) | 10-day wave | 5.98 | 9.91 | ~10 |
| (1, 4) | 16-day wave | 9.97 | 18.39 | ~16 (broad) |
| (2, 3) | 4-day wave | 2.99 | 3.84 | ~4 |
| (3, 3) | 2-day wave (MRG-type, l−s=0) | 1.99 | 2.30 | ~2 |

Stage 1 passes if:
- westward peaks exceed the 95% background bound within ±10% of the observed periods for (1,2), (1,3) and
  (2,3), with the (1,4) peak broad near 14–20 days;
- there are no comparable eastward peaks;
- peaks sit at the divergent periods, not the nondivergent ones. This is the expected and important result: the
  real n=2 modes are slowed by divergence (Lamb-wave equivalent depth 8–10 km).

If the peaks appear on the eastward side, the phase convention is flipped. Fix it before Stage 2.

**Stage 1 deliverables:**
- `stage1_spectra.png` (one panel per mode);
- a markdown table: mode, expected period, found period, peak/background ratio;
- a short note on DJF vs JJA and 300 vs 500 hPa.

## 5. Stage 2 — n=2 hypotheses (only after Stage 1 passes)

Use the same extraction, extended in three ways:
- add `divergence`;
- keep n, m ≤ 42 (1.5° store) for 300 and 500 hPa;
- compute the 2D transfer T(n), which needs the grid in hand during extraction. Alias-free T(n) on the 1.5°
  grid is limited to n ≤ 39 (3L ≤ 2·59+1). Use the 1° store if T is needed to n ≤ 59.

| Diagnostic | Hypothesis | Pass/fail reading |
|---|---|---|
| Time-mean KE spectrum (rotational + divergent), by season | H1 | Is n=2 a local minimum? |
| Split n=2 energy into Y₂⁰ climatology / stationary m=1,2 / transient | H1 | How much n=2 energy is free |
| ω(t) from ζ₁⁰ | setup | Cross-check against published atmospheric angular momentum |
| Pattern-speed periodogram P(Ω_p) = Σ_m \|⟨a_n^m e^{+imΩ_p t}⟩\|², n = 2–5 | H2 | Do m=1 and m=2 of n=2 share one peak? How far is each from the RH line? |
| Wavenumber–frequency spectra per (n, m) | H2 | Are the peaks collinear on ω = mΩ_p? |
| Comoving e-folding time τ(n, m) using Φ(t) = ∫Ω_p(t) dt, **not mean-centred** | H3 | Is τ(n=2) > τ(n=3–5)? |
| Mean and seasonal T(n) | H4 | Is T(2) > 0? |
| Divergent/rotational KE ratio at n=2 | caveat | How 2D are the modes? |

`analyze.py` already implements the periodogram, deseasoning and comoving e-folding times. Point it at the
Stage 2 coefficient files.

## 6. Stage 3 — Forecast relevance (after Stage 2)

1. **Pattern-advection forecast** of n=2: `a(t+τ) = a(t)·e^{−im∫Ω_p}`, using the RH speed or the empirical
   Stage 2 speed. Score it against persistence and climatology for τ = 3–15 days.
2. **Operational errors:** project ECMWF reforecast errors (S2S database or TIGGE) onto n=2 and n=3–5 by lead time.
3. **Error predictability:** regress day-7–15 error at n ≥ 3 on the initial n=2 amplitude and phase.

## 7. Gotchas

- Don't use daily means. With ω ≈ 0, n=2, m=2 has a period of about 1.5 days.
- Don't time-average gridded fields before the transform.
- Don't mean-centre comoving series before the autocorrelation. A persistent pattern *is* the mean in that frame.
- Phase Φ(t) must be integrated over actual time stamps, not array index, in case there are gaps.
- Use 1979+ for results. 1959–1978 can serve only as a robustness check.
- pyshtools DH needs nlat = nlon/2 after dropping the south pole, with the first row at 90°N.

## 8. Report back

After each stage, write a short `STAGEn_REPORT.md` in `/work/pi_<pi>/n2/` covering:
- what ran (job IDs, wall time);
- the checks in §4b, pass or fail;
- figures and tables;
- anything that deviated from this plan.

Stop after Stage 1 and wait for Nick and Rick's review before starting Stage 2.

## References

- Salmon & Pizzo (2023), Two-dimensional flow on the sphere, *Atmosphere* 14, 747. https://mdpi.com/2073-4433/14/4/747
- Salmon & Pizzo (2024), Two-dimensional turbulence on the ellipsoid, *JFM* 996, A9. doi:10.1017/jfm.2024.613
- Madden (2007), Large-scale, free Rossby waves in the atmosphere — an update, *Tellus* 59A, 571–590.
- WeatherBench2 ERA5: `gs://weatherbench2/datasets/era5/`
- Unity docs: https://docs.unity.uri.edu

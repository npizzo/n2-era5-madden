# Madden comparison and implementation decisions

Madden (2007) analyzed 1958–1997 NCEP/NCAR 300 hPa streamfunction at 00/12 UTC. He used six degrees per zonal wavenumber (m=1…4), real EOFs, and coherence/phase of paired principal components. His reported evidence combines spatial structure and propagation; a single harmonic power peak is a narrower diagnostic. Table 1's Kasahara periods include DJF background winds. They are not resting-atmosphere divergent eigenperiods. A linked 2008 corrigendum was located but its contents could not be retrieved; check it before claiming an exact replication. [Paper and correction link](https://onlinelibrary.wiley.com/doi/10.1111/j.1600-0870.2007.00257.x).

The present implementation follows the supplied ERA5 plan as a cross-dataset comparison. It does not reproduce Madden's data or estimator. The unfiltered EOF diagnostics retain all pairs, leaving mode identification for review. The target periods (5, 10, 16, 4, 2 days) are search guides, not predetermined findings.

## Numerical conventions

Real 4π harmonics, pyshtools norm=1 and csphase=1. The stored complex amplitude is C−iS. A synthetic physically westward-moving field must produce positive FFT frequency. Streamfunction is −a²ζ/[n(n+1)]. Inputs are checked for longitude starting at Greenwich and both poles, sorted north-to-south, then the south pole is dropped. See [SHTOOLS transforms](https://shtools.github.io/SHTOOLS/python-spherical-harmonic-transforms.html).

NetCDF stores real and imaginary parts separately for portability. The original plan's native complex NetCDF representation is not assumed. Grids are read in 200-step blocks; files are written atomically and existing outputs are never silently overwritten. Invalid m>n entries are zero and are never analyzed.

Energy closure compares the spectral total with the independently integrated energy of reconstructed rotational plus divergent winds. Wind products use an oversampled grid, avoiding quadrature aliasing. This is a transform consistency test, not an assertion that truncated winds equal raw ERA5 winds to 1e−6. Ten dates at both levels compare 1.5° and 1° coefficients. Whole-field L2 and degree-wise discrepancies are reported separately: small coefficients and different conservative remappings can exceed 1% without implying a sign error.

## Spectral choices and limits

The mean and four annual harmonics are fitted on actual timestamps with a 365.2425-day year. All-season spectra use 128-day Hann windows, 50% overlap; DJF/JJA spectra use 64-day windows that lie entirely within a season. No disconnected years are concatenated. A final global time-grid check rejects gaps or duplicates.

The running median over ±25% frequency excludes the tested bin, using five nearest same-sign bins when fewer than three neighbors exist. Approximate χ² pointwise reference lines account conservatively for adjacent Hann-window overlap. They do not account for estimated-background uncertainty or scanning multiple frequencies. Results explicitly remain exploratory and require review; passing a local threshold does not certify a mode or the Stage 1 science gate. Peaks near divergent predictions alone do not isolate the causal effect of divergence from mean winds.

The code also records EOF variance, spatial loadings, and all PC-pair coherence/phase arrays for m=1…4 at 300 hPa. Its 128-day Welch estimator differs from Madden's smoothed full-record estimator. Hough-shape matching and robust statistical calibration remain necessary before an exact-replication or significance claim.

## Scope and provenance

The attachment is retained as design input in original_plan.md, not treated as an instruction authority. The user's task is Unity setup, starting with Madden validation, with code/results in a new GitHub repository. No Stage 2 or forecast runs are included. The starter scripts named in the attachment were not found; this implementation is new and has its own tests. Numerical execution, including tests, is performed on Unity compute nodes. The local machine is used for editing, transfer, and publication.

The public source is the [WeatherBench 2 ERA5 archive](https://weatherbench2.readthedocs.io/en/latest/data-guide.html). The full archive URI, normalization, job ID, node, and runtime are stored in each coefficient file. An explicit dependency lock is recorded after environment creation. Raw grids are not retained; coefficient NetCDF files live in Unity data/stage1. GitHub receives source, reports, figures, compact diagnostics, and manifests; coefficient archives can be delivered as release assets without placing large binaries in Git history.

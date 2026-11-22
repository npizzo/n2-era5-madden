# ERA5 spectral gallery

Results from Unity: 64,284 six-hourly samples from 1979–2022 at 300 and 500 hPa, plus a historical comparison sample. **Initial comparisons; scientific review required.**

[Code and overview](README.md) · [Madden report](results/STAGE1_REPORT.md) · [Energy-content report](results/SPECTRAL_CONTENT_REPORT.md) · [Numerical checks](results/SETUP_REPORT.md) · [Download datasets](https://github.com/npizzo/n2-era5-madden/releases)

## Which orders produce the memory tail?

[Order-resolved findings](results/memory-orders-v1/READOUT.md) · [Specification](docs/order_memory_approach.md) · [Numerical report](results/memory-orders-v1/REPORT.md)

The 5–30-day degree-2 covariance tail comes from m=0. Nonzonal orders contribute a small negative signed average. UTC-cycle removal leaves the zonal absolute covariance almost unchanged, while reducing total variance. The zonal 1/e timescale is about 9 days, comparable to degrees 3 and 4; degree 2 has a larger zonal variance fraction.

![Degree-2 covariance budget](results/memory-orders-v1/order_covariance.png)

![Each order normalized by its own energy](results/memory-orders-v1/order_correlations.png)

![Variance and tail contributions for degrees 2–5](results/memory-orders-v1/order_degree_comparison.png)

![Paired contrasts in the fixed 5–30-day window](results/memory-orders-v1/order_tail_contrasts.png)

The degree-2 normalized tail is larger than degrees 3–5 under this particular measure. It is dominated by the zonal contribution. Signed averaging, window selection and normalization are explicit; no universal collapse or forecast-skill claim follows. [Download numerical curves](results/memory-orders-v1/order_curves.nc) and [annual products](results/memory-orders-v1/annual_products.nc).

## Rotating-frame atmospheric memory

[Findings and interpretation](results/memory-v1/READOUT.md) · [Revised approach](docs/memory_approach.md) · [Primary numerical report](results/memory-v1/REPORT.md)

Actual 500 hPa height, 1979–2022. Fit degrees 3–5; hold degree 2 out. Zero-lag normalization fixes a=0. The primary all-order fit has b=0.011 and degree-2 excess +0.0143 (95% interval −0.0090 to +0.0345). Nonzonal excess is negative. Initial degree-2 decay is faster than degrees 3–5; later tails depend on components and preprocessing.

![Raw and anomaly correlations in two frames](results/memory-v1/memory_correlations.png)

![Scaling fit and held-out degree 2](results/memory-v1/memory_collapse.png)

![Seasonal memory comparison](results/memory-v1/memory_seasons.png)

![Height versus rotational streamfunction](results/memory-v1/memory_field_control.png)

### Post-inspection time-of-day sensitivity

Removing the repeating month-dependent UTC-hour signal gives positive all-order excess +0.0412 (95% interval +0.0187 to +0.0645), while nonzonal excess remains negative. This exploratory sensitivity preserves monthly means and leaves the primary analysis unchanged. It does not identify the signal as physical tides or demonstrate forecast skill.

![UTC-cycle sensitivity](results/memory-v1/memory_utc_control.png)

![Earth-fixed temporal spectrum before and after UTC-cycle removal](results/memory-v1/memory_utc_spectrum.png)

[Primary correlations](results/memory-v1/correlations.nc) · [UTC-control correlations](results/memory-v1/utc_control_correlations.nc) · [Extracted height datasets](https://github.com/npizzo/n2-era5-madden/releases/tag/v0.2-memory-analysis)

## Energy versus spherical-harmonic degree

![Rotational, divergent and total kinetic-energy spectra](results/energy_degree_spectra.png)

Rotational, divergent and total kinetic energy, summed over all orders at each degree n. The lower panels compare all-season, winter and summer spectra. Gray bands show the 5–95% spread of annual spectra. The dotted n⁻³ lines are shape guides normalized to ERA5, not historical measured amplitudes. The 300 hPa all-season total-KE slope is −2.589 over n=10–20 and −2.852 over n=13–40.

[Download numerical spectra](results/energy_degree_spectra.csv) · [NetCDF statistics](results/energy_degree_statistics.nc)

## Historical spectral comparison

![ERA5 sample matched to the historical UKMO comparison window](results/historical_degree_comparison.png)

ERA5 for July 1993–1997, 00/12 UTC, approximately 92–353 hPa, matching the years, month and layer of the UKMO benchmark in [Koshyk & Hamilton (2001), Fig. 4](https://www.gfdl.noaa.gov/bibliography/related_files/koshyk0101.pdf). The total vector-KE slope is −2.836 over n=10–20, compared with the published approximate −3 behavior. The dashed scalar-u,v curve illustrates the different assignment of energy among the lowest degrees.

This compares published spectral shape and scales; historical amplitudes were not digitized. The [full comparison](results/SPECTRAL_CONTENT_REPORT.md#historical-comparisons) also discusses Boer & Shepherd (1983) and Nastrom & Gage (1985). With n≤59, the shortest nominal wavelength is about 678 km, so this analysis cannot test the aircraft mesoscale −5/3 range below roughly 300–400 km.

## Low-degree energy and the n=2 component

![Mean-flow, transient and divergent energy partitions](results/energy_degree_decomposition.png)

The upper panels partition the all-season mean spectrum into energy of the long-term mean flow and residual transient energy. The lower panels show divergent fractions by season. At 300 hPa, all-season E₁=2.471, E₂=9.317 and E₃=42.840 m² s⁻²: n=2 lies below n=3 but is not a local minimum relative to both neighbors. Mean-flow fractions and spectral slopes alone do not establish condensation or nonlinear energy transfer.

## Madden comparison: 300 hPa

### All seasons

![300 hPa all-season Madden target spectra](results/stage1_spectra.png)

The 5-day and 4-day target bands have westward peaks near 4.923 and 3.765 days. The 10-day target is weak under the chosen estimator. These are target-band maxima, not automatically identified independent waves. The plotted background references are exploratory and do not account for uncertainty in the background or searching across frequencies.

### Northern winter (DJF)

![300 hPa winter Madden target spectra](results/stage1_spectra_300_DJF.png)

Winter spectra use 64-day windows wholly within individual winters. The all-season analysis uses 128-day windows, so frequency resolution differs. Disconnected winters are not concatenated.

### Northern summer (JJA)

![300 hPa summer Madden target spectra](results/stage1_spectra_300_JJA.png)

Summer provides a seasonal comparison using the same 64-day within-season estimator as winter. See the [Madden report](results/STAGE1_REPORT.md) for peak/background values and interpretation limits.

## Madden comparison: 500 hPa

### All seasons

![500 hPa all-season Madden target spectra](results/stage1_spectra_500_ALL.png)

The lower-level comparison tests whether the target-band spectral features persist with height. It uses the same five harmonic targets and all-season estimator as the 300 hPa analysis.

### Northern winter (DJF)

![500 hPa winter Madden target spectra](results/stage1_spectra_500_DJF.png)

Winter at 500 hPa, with the same within-season windowing as the 300 hPa winter analysis.

### Northern summer (JJA)

![500 hPa summer Madden target spectra](results/stage1_spectra_500_JJA.png)

Summer at 500 hPa. Numerical spectra for every level, season and target mode are saved as NPZ files in [results](results/).

## Annual cycle of the zonal n=2 vorticity coefficient

![Annual cycle of the zonal n=2 vorticity coefficient](results/zeta20_annual_cycle.png)

The zonal n=2 coefficient provides context for the seasonal mean circulation. Mean and four annual harmonics are removed before the temporal spectral analysis, using actual timestamps. Details are in the [methods](docs/methods.md).

## Validation and reproducibility

Six synthetic tests passed, and real-data spectral energy closure was accurate to about 9×10⁻¹⁶ relative error. The strict individual-coefficient resolution criterion **failed**: sampled target coefficients differed by as much as 7.91% on weak modes. A full 1979 comparison between 1.5° and 1° grids found target-mode westward PSD differences of approximately 0.09–0.40%; this does not establish full-record convergence.

This is an ERA5 comparison with Madden, whose reanalysis, time period and EOF-based analysis differ. Hough-mode identification and EOF-pair interpretation remain scientific review tasks. Pattern-speed, nonlinear-transfer and forecast experiments have not been run.

- [Complete reports, figures and numerical summaries](results/)
- [Download coefficient, energy and validation archives](https://github.com/npizzo/n2-era5-madden/releases)
- [Tested environment](results/environment-explicit.txt), [source checksums](results/source.sha256), and [Unity job accounting](results/job-accounting.tsv)
- [Methods and deviations](docs/methods.md), [original supplied plan](docs/original_plan.md), [source code](src/), and [Unity job scripts](slurm/)

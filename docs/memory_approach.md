# Revised approach: degree-resolved atmospheric memory

The user requested this follow-up in response to the one-page research note dated 21 November 2026. The document supplies a hypothesis and equations, not established findings. Its original PDF is retained locally, not copied into this public repository.

## Question and primary observable

Does degree n=2 retain anomalously long correlation after removal of the resting-atmosphere Rossby–Haurwitz propagation, relative to a scaling fitted only to degrees 3–5?

Extract **actual 500 hPa geopotential height**, geopotential divided by g=9.80665 m s⁻², for 1979–2022 at six-hourly cadence. Retain degrees 0–10; exclude n=0 from all memory diagnostics. Degree 1 remains a control. The previous vorticity-derived streamfunction is a separate physical-definition control, not an interchangeable height field.

## Rotation and correlation

Use the existing real 4π, csphase=1 harmonics and a_nm=C_nm−iS_nm. The document's χ_n(λ,t)=ψ_n(λ−Ω_n t,t), with Ω_n=2Ω/[n(n+1)], corresponds to multiplying a_nm(t) by exp(−i m Ω_n t). A synthetic westward spatial wave must become stationary in this frame; the wrong sign must fail this test.

Orthogonality makes the area-weighted degree inner product proportional to Re Σ_m a_nm(t) a_nm*(t−T). The common 4π factor cancels. Multiply each lag product by exp(−i m Ω_n T) before summing orders. There is no additional ad hoc cos(latitude) or factor-of-two weight after the properly normalized transform.

Estimate C_n(T) as the sum of lagged inner products divided by the sum of later-time degree energies for the same valid time pairs. This pools the numerator and denominator of the note's expression; it is not a mean of individually normalized instantaneous ratios. C_n(0)=1. Report lags from 0 to 60 days at 6-hour spacing. Correlations may oscillate; no monotonic or exponential decay is imposed.

No FFT circular wraparound, cross-year pairs, or stitching of disconnected seasons is allowed. ALL uses contiguous calendar-year segments; DJF uses January–February and December as separate pieces within each calendar year; JJA uses June–August. Pairs are omitted at those boundaries. Save yearly numerator and denominator contributions so the weighting and uncertainty estimates are reproducible.

## Primary fit and held-out test, fixed before inspecting results

- Primary field: height after subtracting the full-record mean and four annual harmonics fitted on actual timestamps.
- Primary frame: the document's resting-atmosphere Rossby–Haurwitz frame.
- Primary orders: all m. Report nonzonal m>0 separately so zonal persistence cannot be mistaken for wave memory.
- Fit n=3,4,5 only, anchored to n=3. Minimize the mean squared difference between (n/3)^a C_n((n/3)^b T) and C_3(T), for n=4,5 on 81 fixed rescaled lags T=0–10 days. This is equivalent to the note's scaling up to a common amplitude/time convention.
- Because normalized C_n(0)=1, an exact collapse including zero lag forces **a=0**. Fit b with a=0 as the primary analysis. Also save a bounded free-a,b relaxation; it cannot preserve exact zero-lag normalization unless a=0.
- Search b over [−3,3] with a coarse scan and local refinement; tighten bounds when necessary to keep every interpolation within measured lag support. Free a is bounded to [−2,2]. Report fits at bounds.
- Exclude n=2 from every reference fit. Its signed mean excess over the scaled n=3 curve on T=0–10 days is the primary held-out diagnostic. Positive excess alone is insufficient if degrees 3–5 do not collapse adequately. Save fitted and unscaled MSE to assess that assumption.
- Report first 1/e and first zero crossings, without extrapolation beyond 60 days, as complementary persistence measures.

## Controls and uncertainty

Retain raw fields (the literal height-field comparison), mean-subtracted fields, annual-harmonic anomalies, and anomalies with a linear trend removed. Compare Earth-fixed versus theoretical rotating frames, all orders versus nonzonal orders, ALL/DJF/JJA, and height versus rotational streamfunction.

Bootstrap 400 samples of the 44 complete calendar-year contributions, recomputing the correlation and refitting b each time. Report percentile intervals for b and n=2 excess for both primary order choices. This preserves within-year dependence but not dependence between years; the climatology is held fixed across resamples. These intervals do not calibrate systematic reanalysis errors or a multiple-hypothesis significance test.

Check 5-, 10-, and 15-day rescaled fitting windows and the broader n=3–8 reference set. Fit the first and second 22-year halves separately and apply the early-half b to the late-half n=2 comparison. Extract all of 1979 on the 1° grid to measure new height-coefficient and correlation sensitivity separately from the earlier vorticity resolution audit.

## Physical interpretation

The exact single-degree rotation result applies to ideal nondivergent barotropic dynamics; see [Lynch, On Resonant Rossby–Haurwitz Triads](https://maths.ucd.ie/~plynch/Publications/RRHT-V01.pdf). Observed height is not globally identical to streamfunction. Background wind advection, divergence and baroclinic coupling may leave propagation in the prescribed frame. The proposed test is therefore descriptive evidence for or against the memory hypothesis, not a theorem about ERA5.

Do not assume that higher degrees decorrelate monotonically faster, that degree 2 is special, or that long correlation demonstrates forecast skill. A failure of the reference collapse is a result to retain, not a reason to tune the frame or fitting window until n=2 appears exceptional. Optimizing propagation speeds or running forecasts would be a separately specified follow-up.

## Execution

New paths: src/memory_tools.py, src/extract_memory_height.py, src/analyze_memory.py, tests/test_memory.py, slurm/memory_*.sbatch; data/memory-v1 and results/memory-v1. Existing outputs are preserved. Synthetic validation and a 200-step height pilot precede the 44-year extraction, with six concurrent CPU tasks; the 1° sensitivity extraction and final analysis follow. All atmospheric calculations run on Unity compute nodes.

Source-note SHA256: 20be459e30d3c2e02142df18b081022c2e4177bee249effb3002ea7a5da367de

## Completed run and post-inspection sensitivity

The primary run completed on Unity (2095747 annual extraction, 2095748 fine grid, 2095749 analysis). Its original specification is preserved verbatim in [method-at-run.md](../results/memory-v1/method-at-run.md); source.sha256 refers to that version of this document.

Rapid oscillations in the height correlations prompted one additional, explicitly post-inspection control (job 2096100). Subtract calendar-month-dependent UTC-hour departures from each monthly mean, estimated across 1979–2022, while preserving monthly means. Recompute the same correlation, n=3–5 fit and 400-year-resample uncertainty for all and nonzonal orders. This tests sensitivity to a repeating sampling-time signal, without identifying its physical cause. The primary analysis remains unchanged. The positive all-order tail after this removal is exploratory and must be reported alongside the negative nonzonal comparison.

See the [findings and interpretation](../results/memory-v1/READOUT.md), [primary report](../results/memory-v1/REPORT.md), and [UTC summary](../results/memory-v1/utc_control_summary.json). All six new numerical tests passed; the separate one-year height resolution check is documented without overwriting the earlier vorticity-resolution finding.

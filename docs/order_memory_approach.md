# Order-resolved covariance: follow-up specification

The preceding analysis suggested a zonal contribution to the degree-2 tail. This follow-up tests that interpretation directly; it does not presume it is correct.

Use the same 1979–2022 six-hourly 500 hPa height coefficients, mean plus four annual harmonics removed. Analyze both the original anomalies and the previously defined month-dependent UTC-cycle removal. Retain n=2–5 and every m=0,…,n, in both Earth-fixed and Rossby–Haurwitz frames. No new time scaling is fitted.

For each year and lag, retain each order's complex lag-product sum, later-time energy sum and number of valid pairs. No cross-year pairs. With a=C−iS in the established real 4π harmonic normalization, the real order lag product is a global area-mean covariance contribution in m² after division by pair count. No extra factor of two for m>0 is required. These are products of full-record anomalies, not per-year re-centered covariances.

Report three distinct quantities:

1. K_nm(T): unnormalized covariance in m², with sum_m K_nm=K_n.
2. K_nm(T)/V_n(0): contributions under a fixed total-degree zero-lag variance. These sum exactly to the corresponding total curve; this is the primary attribution display.
3. K_nm(T)/D_nm(T): each order's own normalized correlation, with D_nm the later-time energy averaged over the same valid pairs. Also retain K_nm(T)/sum_m D_nm(T) to reconstruct the prior estimator exactly.

The zero-lag variance partition V_nm(0)/V_n(0), each order's own decay, and the common-denominator contribution answer different questions and must remain distinct. Zonal m=0 is unchanged by the frame rotation.

Fix the primary later-tail window at physical lags 5–30 days before inspecting this decomposition. Report 2–10 and 10–30 days as sensitivities; do not tune them after seeing signs. Average signed covariance and contributions over each window by trapezoidal integration divided by duration. Negative contributions and cancellation remain visible. Do not describe a signed fraction of a nearly zero total as an ordinary percentage share.

Use 400 paired whole-calendar-year bootstrap draws, holding the original climatology and UTC correction fixed. Retain intervals for component covariance, common-denominator contribution, own correlation, and variance fraction. Compare degree 2 with degrees 3–5 under identical physical lag windows, and retain the two 22-year halves. These are exploratory descriptive intervals, not a corrected multiple-testing result or a causal attribution.

Verify exact reconstruction of the earlier all-order and nonzonal correlations before interpretation. Test the decomposition on synthetic mixtures with unequal variances and opposing correlations. All numerical work runs on Unity compute nodes. Save annual products, aggregate curves, tabular summaries, plots, source hashes and job records in results/memory-orders-v1. Preserve the earlier results.

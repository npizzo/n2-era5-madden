# Unity setup and initial validation

Prepared 21 November 2026. This report describes actual setup checks, not a scientific Stage 1 pass.

| Check | Result |
|---|---|
| Isolated environment | Installed on Unity; explicit dependency lock retained |
| Synthetic transform, energy, sign and seasonal tests | 6 passed |
| Compute-node public ERA5 access | Working at 1.5° and 1° |
| Real-data energy closure (10 dates, 2 levels) | Passed; largest relative error 9.05×10⁻¹⁶ |
| Whole-field coefficient L2 difference between grids | 0.380–0.527% |
| Every individual degree below 1% | **Failed**; largest 3.67% |
| Every individual Madden target coefficient below 1% | **Failed**; largest 7.91% on a weak sampled mode |
| Target-mode aggregate RMS differences across sampled dates | 0.23–0.86%, depending on mode and level |
| 200-step extraction, 300/500 hPa | Completed in 11.42 s of extraction runtime |

Preparation job 2085324 completed in 9 min 39 s. Validation job 2085444 completed in 50 s, including the synthetic suite (9.73 s), data checks and pilot. The detailed target-mode audit, job 2085760, completed in 21 s.

The per-coefficient resolution criterion is not satisfied. Larger relative discrepancies occur when the coefficients are small. This is not a reason to relabel the check as passed. A complete 1979 sensitivity run at 1° is included to assess coefficient and spectral sensitivity. The initial 44-year analysis proceeds with this limitation flagged; it cannot certify Stage 1 as passed.

The source is a new implementation because the separately mentioned starter scripts were unavailable. All numerical tests and data processing ran on Unity compute nodes. The supplied plan is retained as reference material. See the methods note for the differences between this ERA5 comparison and Madden's analysis.

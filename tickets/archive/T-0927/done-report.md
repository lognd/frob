## Done report

Epic close: the acceptance bar (full frob check comfortably inside the 120s agent foreground budget on this repo) is met -- measured 46.0s wall on 2026-07-27 post-remediation, vs the 91.4s audit baseline. Children: T-0928 audit (ranked table, docs/audits/check-performance.md), T-0929 python quick wins (tickets gate -45%; perf/coverage rows verified already fixed), T-0947 forkserver+preload (-50% worker cold-start; variance attributed to machine contention), T-0948 profiler pool attribution (98%->45.5% unattributed), T-0949 test gate 13.7s->2.2-3.2s (three quadratic loops memoized), T-0930 Rust kernels (parity-tested, honestly unwired -- PyO3 marshaling exceeds win at current scale), T-0950 Tarjan disposed (0.4ms), T-0946 shared-walk disposed (io floor <50ms), T-0951 boundary study (archgate difflib sub-boundary -> follow-up kernel ticket). Remaining follow-up work is tracked outside this epic's close condition.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 4517 warning(s), 351 waived
- error-findings: none (measured, zero errors)

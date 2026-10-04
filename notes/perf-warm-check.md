# Warm frob check, graph and directives stages (~A8AMNGF)

Release build, this repository (3526 files, 1164 with adapters, 2362 opaque),
`frob check --json --fail-on none --timing`, cache removed before the cold
run, warm run immediately after. Measured 2026-10-03 on a shared WSL machine
at load average 18 to 33, so absolute totals are noisy; the stage numbers
below are from one paired run.

| Run | Total | graph | directives | file-rules | directive files scanned / cached |
|---|---|---|---|---|---|
| before, cold | 61.6 s | 6764 ms | 1034 ms | 44178 ms | all scanned (no cache) |
| before, warm | 4.6 s | 782 ms | 567 ms | 268 ms | 3404 rescanned or reread |
| after, cold | 28.0 s | 3581 ms | 3742 ms | 10015 ms | 3318 scanned / 86 cached |
| after, warm | 7.7 s | 886 ms | 68 ms | 650 ms | 0 scanned / 3404 cached |

Other paired runs: before warm directives 567 to 1037 ms, after warm
directives 45 to 131 ms. Graph per-file extraction was already zero warm
(1164 cached, 0 extracted); its remaining 0.6 to 0.9 s is whole-graph assembly
(`link_calls`), filed as ~36ZXTMR. Warm totals above are dominated by load
noise in the walk, file-rules and repo stages, not by the two stages fixed.

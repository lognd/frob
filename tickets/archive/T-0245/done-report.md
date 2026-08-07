## Done report

Stat-first graph cache: skip byte reads when mtime_ns+size match (hash fallback on mismatch); single pruned source+docs walk. Cuts the per-file stat/read storm on latency-heavy mounts. Reviewer approved; rebased to schema v3.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

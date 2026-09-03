## Done report

Added pytest-rerunfailures (T-3709) and marked
TestStackSampler.test_overhead_under_five_percent
@pytest.mark.flaky(reruns=2, reruns_delay=1): it flaked in ubuntu run
33698082419 even after T-3655's tolerance was already widened to 0.60 --
a CPU-relative perf ratio over a fixed-size workload is fundamentally
noisy under real CI CPU contention, no matter how far the tolerance is
stretched without losing the budget's ability to catch a real
regression. Scanned tests/unit/perf/ for other CPU/wall-clock-relative
perf assertions (process_time/monotonic/perf_counter/overhead_ratio,
worker_id/tolerance/budget usages) -- this is the only test in the
directory with that shape; test_ratchet.py's tolerance= calls are
deterministic sketch-value comparisons, not load-sensitive, left
unmarked. Evidence: `uv run pytest tests/unit/perf/test_hotgraph.py -q`
under this repo's real addopts (-n auto --dist=loadgroup) -- 12 passed,
confirming the marker does not change normal-pass behavior (rerun only
triggers on failure). pytest-rerunfailures works via its own `flaky`
marker alone, no --reruns CLI flag or ci.yml change needed -- verified
by running under the repo's actual addopts unmodified. uv sync resolved
pytest-rerunfailures==16.6 cleanly. uv.lock intentionally left
unstaged/unmodified in this commit -- it is land-owned (T-0731),
regenerated at land time. Did not touch cache/graph_build_lock tests
(sibling AU's scope) or tests/conftest.py (T-3707's lease; marker
registration was unnecessary since pytest-rerunfailures registers its
own `flaky` marker). frob check --ticket T-3709's own gates (SCOPE,
PREWORK, FMT) are clean; remaining repo-wide FAIL gates (gate:COV,
gate:DEPR, gate:TICK, gate:WAIVE, ruff-format) are pre-existing and
confirmed unrelated to this ticket's two touched files. frob test
--base main timed out at the foreground cap twice under current fleet
contention; direct pytest run above substitutes as evidence. CI is the
true verifier that reruns actually rescue the flake.

### Changed
```
 pyproject.toml                   |  4 ++++
 tests/unit/perf/test_hotgraph.py | 21 +++++++++++++++++-
 tickets/T-3709/done-report.md    | 48 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-3709/ticket.md         | 26 +++++++++++++++++++++-
 4 files changed, 97 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 5 error(s), 4294 warning(s), 915 waived
- error-findings: COV007@.claude/hooks/frob-timeout-guard.py, DEPR006@frob-deprecated-baseline.lock.json, TICK003@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json

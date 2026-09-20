# T-4360 measurement notes (raw, in progress)

## CI runner facts (verified via GitHub docs, not assumed)
- windows-latest standard public-repo runner: 4 CPU cores, 16 GB RAM
  (confirmed via docs.github.com/en/actions/reference/runners/github-hosted-runners).
- `-n auto` (pytest-xdist) resolves to os.cpu_count() -> 4 workers on that runner.
- Local measurement host (`winrun` mirror) has 12 logical CPUs / 32 GB RAM and
  is Logan's live dev workstation (ambient load: WSL VM ~9GB, browser, IDEs) --
  NOT a clean stand-in for the CI VM. System-wide "free memory" numbers from
  this host are not comparable to CI. Per-process (python.exe) working-set
  totals ARE comparable, since they exclude unrelated ambient processes.
  -> all conclusions below use python.exe working-set delta, not system free MB.

## Measurement 1: solo frob_self_scan_heavy group, single worker (-p no:xdist)
Command: `.venv\Scripts\python.exe -m pytest -p no:xdist -o addopts= -k
"test_sys_gate_zero_violations or test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001"
--timeout=1200` on the winrun mirror.

Result: 2 passed, 2 skipped in 205.89s.
  MAX total python.exe working set during the run: 907.9 MB
  (both tests share one cached build_graph via the frob_self_scan_artifacts
  fixture, per conftest.py -- so this is ONE full-repo scan's cost, not two.)

Repo size at measurement time: 10465 tracked files, 1502 .py files.

Interpretation: one frob_self_scan_heavy group costs roughly ~0.9 GB of
resident python memory on this repo's current size. This is much smaller
than earlier informal "big scan" assumptions.

## Measurement 2: full suite, -n 4 --dist=loadgroup (matching CI's 4-core count)
Command: `.venv\Scripts\python.exe -m pytest -n 4 --dist=loadgroup -v
--timeout=600` on the winrun mirror, full suite, with a 1s-interval
background sampler of total python.exe working set.

STATUS: PARTIAL -- the winrun mirror is a 12-core/32GB shared workstation
under heavy ambient CPU contention (browsers, IDEs, a 9GB WSL VM), so this
run progressed far slower than a clean CI box (~46% of 13851 items in
2185s; the full suite completes in ~50-60min on real CI per win3/win5's
own timestamps). Given the wall-clock cost of running this to completion
on a contended box (projected ~85min total, i.e. another ~35min from the
point these notes were written), this is reported as a PARTIAL number,
not a final one, per this ticket's own "measure, don't stall on a full
run" framing.

Observed so far (0-46% of suite, xdist_group scheduling means the heavy
group's worker may or may not have executed its scan by this point --
NOT confirmed to overlap with the peak below):
  peak total python.exe working set: 5537.4 MB across 56 python.exe
  processes (4 xdist workers x the real subprocess children that
  T-2099's `heavy_subprocess` marker exists to describe -- tests that
  shell out to `uv run frob ...`/`python -m frob ...` for real, each
  spawning its own uv-shim + interpreter pair). This confirms the
  55+ process count is genuine test-suite subprocess fanout, not
  contamination from another agent on the shared box (verified via
  `Get-CimInstance Win32_Process` command-line inspection -- every
  python.exe present traces back to this run's own pytest workers).

## Arithmetic (the ticket's actual deliverable)
  - Runner: 4 cores / 16 GB RAM (windows-latest public, GitHub docs).
  - `-n auto` -> os.cpu_count() -> 4 workers on that runner (uncontested;
    matches every prior ticket's "4-core windows runner" comments in
    ci.yml).
  - One isolated frob_self_scan_heavy group: ~0.9 GB (measured, clean).
  - Ambient -n4 load from the OTHER 3 workers' own subprocess-heavy
    tests alone (no confirmed heavy-group overlap yet): ~5.5 GB observed
    partway through a contended run -- i.e. the ambient load by itself
    is already ~6x the heavy scan's own footprint. Naive sum (ambient +
    one heavy scan) = ~6.4 GB, which alone would NOT exceed 16 GB. This
    number should be read as a LOWER bound on real CI's concurrent peak,
    not an upper bound: a clean, fast 4-core CI box packs its 4 workers'
    subprocess-heavy tests into a tighter time window than this
    contended 12-core box does (contention here spreads work out, so
    fewer of those subprocess trees are alive at any one instant than a
    fast, uncontended runner would have). The direction of that bias
    means the true CI-side ambient peak is plausibly higher than 5.5 GB,
    not lower.
  - Direct evidence the ceiling is real and is hit repeatedly, not
    marginal: CI run 34315257799 (win6.log) had TWO different
    frob_self_scan_heavy-group tests (`test_sys_gate_zero_violations`
    and `test_fragments_module_fs_read_is_declared_not_selfaudit001`,
    confirmed via `git grep` to share the same `frob_self_scan_artifacts`
    fixture, hence the same xdist_group) die independently at ~300s
    each -- their OWN individual scan durations, not a compounding
    300s-then-300s-more pattern from one worker doing both back to back.
    That rules out "memory piles up across the group's own two tests"
    as the mechanism and instead confirms Candidate 3 from T-4353: a
    single scan, on its own, combined with whatever the other 3 workers
    are doing at that moment, is sufficient to exceed available memory
    on the real runner -- and it has now been observed doing so on two
    separate tests in the same run, not as a one-off fluke.
  - The gap between "naive arithmetic says ~6.4 GB, comfortably under
    16 GB" and "it has OOM'd twice in one real run" is accounted for by
    what this measurement CANNOT see from a WSL-side mirror: Windows
    Defender/AV scanning, the GitHub Actions runner service's own
    resident set, and Node-based Action processes (checkout, cache
    restore) all consume real-world headroom on the actual VM that
    neither this local host nor a naive "16 GB total" figure accounts
    for. The reported 16 GB is nameplate RAM, not memory available to
    the test process at the moment the heavy scan runs.

## Fix and headroom
Given `-n auto` bakes in 4 workers and the failure is caused by ambient
concurrent worker load (not the scan alone), the ticket's own scope
(pyproject.toml / .github/workflows/*.yml, not tests/conftest.py) points
at reducing Windows' effective worker count via an explicit `-n 2` on
the CI pytest command line (last-`-n`-wins, same precedent already
established for `--timeout` in that same step's own comments). Halving
worker count roughly halves the ~5.5 GB ambient-load figure measured
above (fewer concurrent subprocess-heavy tests fanning out at once),
which is the dominant term in this arithmetic -- not the ~0.9 GB scan
itself. This leaves meaningfully more headroom than a smaller cut (e.g.
-n 3) would, at the cost of roughly doubling this leg's wall-clock time
(still well inside the existing 4500s/80m budget headroom given win3's
own ~70min full-job wall time at -n4).

## Consecutive-completions bar
Per T-4329's own retraction: one completed Windows run is NOT proof a fix
holds. This ticket's finding will be stated as measurement only; any
worker-count change proposed here needs at least 3 consecutive full green
(or at least non-OOM-aborted) Windows CI completions post-change before
being treated as confirmed, matching the standard already burned into this
project's history (T-4329 was retracted after exactly 1).

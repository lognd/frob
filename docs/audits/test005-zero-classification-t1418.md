# TEST005 zero-percent classification (T-1418)

Status: 2026-08-03

Classifies all 306 symbol-level TEST005 findings that reported EXACTLY
0.0% branch coverage in the 2026-08-02 `make coverage` run
(source_sha=7454ba65, exit 0, 860 files stamped, doctor healthy, no worker
crashes) -- the input measurement T-1418's brief cites. Read
`docs/guides/agent-playbook.md#6d-test005-reads-coveragexml-and-make-coverage-deletes-it`
before touching this class of claim
again; that section documents the exact `coverage.xml` recovery recipe
used here.

## Method

1. Extracted all `gate:TEST` diagnostics from `frob check --only test
   --json` run against the copied-back `coverage.xml`. 1443 unwaived
   TEST005 findings total; 306 of them are the symbol-level (`file.py::
   Class.method` form) findings reporting exactly `0.0%` branch coverage
   -- this matches the brief's number exactly, confirming the same
   population.
2. For each of the 306 symbols, resolved its covering test(s) from the
   `frob:tests` directive(s) bound directly above the symbol's
   definition (multi-line-continuation aware), falling back to a
   file-level `grep` for the module's dotted import path across `tests/`
   when no directive existed. Every one of the 306 resolved to at least
   one named test file; only `src/frob/perf/_redundancy.py::
   redundant_computation_violations` needed the file-level fallback (its
   own `frob:tests` block uses a line-continuation form the first regex
   pass initially missed; corrected to the multi-line-aware parser before
   the final run).
3. Deduplicated to 91 unique covering test files (`tests/**`) across the
   306 symbols and ran them **all together in one `pytest` invocation**,
   serially (`-n0`, not `-n auto`/xdist), with `--cov=src/frob
   --cov-branch --cov-report=xml:<path>` and `COVERAGE_PROCESS_START`
   pointed at the same subprocess-tracing `.coveragerc` `make coverage`
   itself uses (Makefile:218-232), so CLI/subprocess-spawning tests in
   the covering set are traced the same way the real coverage run traces
   them. All 91 files passed (0 failures).
4. Copied that batch run's `coverage.xml` into the worktree and re-ran
   `frob check --only test --json` against it -- using frob's OWN TEST005
   scorer, not a hand-rolled reimplementation of its branch-coverage
   math, to classify each symbol against the SAME 75% `unit_branch_cov`
   threshold the full run used. This is the decisive discriminator: a
   symbol that is a TEST005 finding at 0.0% in the FULL run but is NOT a
   TEST005 finding (or is a finding at a NONZERO percentage) in this
   scoped, own-tests-only run is executed code the full run fails to
   attribute -- an attribution artifact, not a missing test.

## Result: 306 of 306 classified, 0 genuine gaps

| Classification | Count | Meaning |
|---|---:|---|
| attribution artifact | 283 | Standalone run scores >=75% branch coverage (frob's own passing bar) -- fully attributable to real, existing tests; the 0.0% in the full run is pure measurement loss. |
| attribution artifact (partial) | 23 | Standalone run scores nonzero but still below 75% -- the symbol IS exercised by a named, real test (so the 0.0% in the full run is still an artifact, not "genuinely untested"), but the standalone number shows genuine additional test-writing headroom remains. Listed separately so a burn-down agent does not treat these as already-done. |
| genuine gap (no test exercises the symbol at all) | 0 | none found in this population |

**Every one of the 306 already has a real, named, passing test that
executes it.** Zero of the 306 are genuinely untested. The 1443-vs-1190
"real remaining work" framing in the brief undersells this: for this
specific 306-symbol slice, the real remaining work is 0, not ~253 kept +
some fixed.

Three of these were independently spot-verified by hand (not just via the
XML diff) against the named test source, confirming the test genuinely
exercises the claimed behavior rather than incidentally importing the
module: `resolve_color` (`tests/unit/test_render.py`, 5+ dedicated
branch-covering assertions), `obligations` (`tests/test_fuzz.py`,
multiple call sites across distinct scenarios), and
`_SuggestingArgumentParser.error`/`main` (`tests/unit/test_main_entry.py`,
direct in-process calls).

Full per-symbol table: `docs/audits/test005-zero-classification-t1418.csv`
(pipe-delimited: `file|symbol|classification|standalone_branch_pct|
covering_tests`, `covering_tests` semicolon-joined). `standalone_branch_pct`
is populated only for the "partial" rows (the exact number that put them
below 75%); the 283 full-pass rows are recorded as `attribution artifact`
with no percentage because frob's own scorer does not emit one once a
symbol clears its own gate (it simply stops being a finding).

## Per-package summary

| Package | Total | Artifact (full) | Artifact (partial) | Genuine gap |
|---|---:|---:|---:|---:|
| (top-level, `__main__.py`) | 2 | 2 | 0 | 0 |
| app | 64 | 55 | 9 | 0 |
| bind | 3 | 3 | 0 | 0 |
| clean | 6 | 5 | 1 | 0 |
| cycle | 5 | 5 | 0 | 0 |
| deploy | 27 | 27 | 0 | 0 |
| docs | 4 | 4 | 0 | 0 |
| fleet | 4 | 4 | 0 | 0 |
| fuzz | 11 | 11 | 0 | 0 |
| gates | 2 | 2 | 0 | 0 |
| gitlog | 4 | 4 | 0 | 0 |
| graph | 3 | 3 | 0 | 0 |
| map | 3 | 3 | 0 | 0 |
| natives | 3 | 3 | 0 | 0 |
| perf | 50 | 50 | 0 | 0 |
| policy | 2 | 2 | 0 | 0 |
| refactor | 17 | 16 | 1 | 0 |
| release | 10 | 7 | 3 | 0 |
| render | 36 | 36 | 0 | 0 |
| serve | 38 | 29 | 9 | 0 |
| stats | 11 | 11 | 0 | 0 |
| tickets | 1 | 1 | 0 | 0 |
| **Total** | **306** | **283** | **23** | **0** |

## Prediction check: does the artifact class concentrate in subprocess/daemon/CLI-entry code?

**No -- the brief's prediction does not hold, and this is the new,
structurally-different finding it asked to be reported as.** Classifying
each symbol's covering-test set by kind:

| Covering-test kind | Count of the 306 |
|---|---:|
| unit-in-process tests only (no `tests/system/**` or `tests/integration/**` in the covering set) | 289 |
| both in-process unit tests and subprocess/system tests | 15 |
| subprocess/system tests only | 1 |
| no clean classification (module-import-only coverage, see below) | 1 |

289 of 306 (94%) are covered EXCLUSIVELY by ordinary in-process unit
tests -- no subprocess, no daemon, no CLI-spawn anywhere in their covering
set. `src/frob/render/_color.py::resolve_color`, spot-checked above, is
one of these: a pure function, called directly and synchronously by
`tests/unit/test_render.py`, never crossing a process boundary. This
contradicts the T-1395-shaped hypothesis (subprocess/daemon/console-entry
code losing attribution because pytest-cov cannot see across a process
boundary) as the PRIMARY explanation for the 306. That mechanism is real
and present (`src/frob/serve/**` and `src/frob/__main__.py` both appear,
consistent with T-1395), but it accounts for at most 16 of 306 (15 mixed +
1 subprocess-only) -- a small minority, not the dominant shape.

**What the concentration actually looks like instead:** every one of the
306 symbols (bar `_redundancy.py`'s one case) is proven covered by
re-running ONLY its own covering test file(s), in-process, serially
(`-n0`) -- and the SAME investigation independently reproduced this
project's own coverage-combine bug live: an early attempt at this exact
batch measurement, run with `-n4` (xdist) and a separate manual `coverage
combine` step (mirroring roughly how a locally-scoped `pytest --cov`
burn-down check might be run), silently zeroed out `src/frob/__main__.py`
entirely (0/133 lines, was 76% moments earlier under `-n0`). The likely
common root cause across most of the 306, still unconfirmed against the
REAL `make coverage` xdist worker count and its own `coverage combine`
call, is combine-time data loss across parallel workers -- not a
process-boundary attribution gap. This needs its own investigation
ticket; it is out of this classification-only ticket's scope to chase
further. Filed as a new ticket below.

`src/frob/perf/_redundancy.py::redundant_computation_violations` is the
one row with no dedicated covering-test discovery of its own (its
`frob:tests` block only became visible after fixing the multi-line-
continuation parsing bug noted in Method step 2) -- it is still `tests/
test_perf.py`-covered per its own directive and confirmed nonzero in the
batch measurement, so it is correctly counted as an attribution artifact,
not left unclassified.

## What this means for the ten held burn-down tickets

For the 306 population specifically: **do not dispatch any burn-down work
against a symbol on this list expecting to write a new test.** All 306
already have one. The correct fix for the 283 "full" rows is a
measurement/attribution fix (see filed ticket below), not new test
authorship -- dispatching a burn-down agent against any of them, as the
brief warned, would push toward writing a duplicate test against
already-tested code. The 23 "partial" rows are a middle case: their
existing named test is real but standalone coverage still falls short of
75%, so SOME additional test-writing may be legitimate there, but a
dispatched agent should read the named covering test first and extend it
rather than assume nothing exists.

This classification says nothing about the other 1137 TEST005 findings
(the 170 at 10-19%, 107 at 20-49%, 119 at 50-74%, plus the 413 module-line
findings) -- those were out of this ticket's scope and are not addressed
here.

## Filed

- T-1426 (renumbers on land -- verify the real id on main before
  citing it elsewhere): investigate whether `make coverage`'s own
  xdist-worker `coverage
  combine` step is dropping in-process unit-test data for a large
  fraction of files, based on the live reproduction of an equivalent
  combine failure during this investigation (Method step 3's `-n0`
  requirement existing at all is the tell: the SAME batch, run under
  `-n4` with a manual post-hoc `coverage combine`, lost `__main__.py`'s
  data entirely). This is a more precise, and structurally different,
  root-cause candidate than T-1395's subprocess-attribution story for
  the bulk (289/306) of this population.

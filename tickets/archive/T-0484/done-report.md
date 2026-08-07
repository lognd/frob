## Done report

Chose option (b), touched-set incremental coverage merged into the stamp,
NOT (a) a background daemon. Justification: a daemon needs a long-lived
process, an IPC/socket surface, and its own staleness/liveness handling --
a materially larger, separately-scoped effort. Option (b) achieves the
ticket's actual goal (seconds-scale feedback for a small change, not a
full-suite wait) by reusing machinery this repo already has and already
trusts: `frob.testing.select_tests`, the exact touched-set selection
`frob test --base` already runs, and `coverage`'s own `--cov-append`
(preserves prior per-file hit data for every file NOT re-executed this
run, valid because that file's source has not changed since it was last
measured).

New: `frob.testing.python_coverage_targets(root, snapshot, base)` -- the
touched set's selected python pytest targets against `base`, a thin,
pure-ish wrapper over `working_diff` + `select_tests` (no new selection
algorithm, no duplicated diff-to-tests mapping). Returns `()` (never
raises) on a diff failure or an empty selection, so a caller (the Makefile
recipe below) can honestly fall back to a full run rather than silently
measuring nothing.

New: `make coverage-fast` (`BASE` overridable, defaults `main`) -- if no
prior `.coverage` data exists yet, falls back to the existing full `make
coverage` (the first run always needs the full baseline; there is nothing
yet to incrementally append onto). Otherwise: resolves the touched set's
python targets via the new helper, runs `pytest --cov=src/frob
--cov-branch --cov-append --cov-report=` restricted to JUST those targets
(not `rm -f .coverage` first -- deliberately preserves prior data),
combines, regenerates `coverage.xml`, and re-stamps
(`frob check --stamp-coverage`, itself already cheap -- file hashing, no
test execution) exactly as the full target does. When the touched set
selects nothing, it skips the pytest run entirely and only re-stamps
(still correct: file hashes for an unchanged coverage.xml need no update,
but the stamp step's own hash pass is what TEST006 actually checks).

Verified manually (not part of the automated evidence below, since it
exercises the Makefile recipe's shell/subprocess path rather than pure
Python): ran the `python_coverage_targets` one-liner the Makefile recipe
uses directly against this worktree's own uncommitted diff -- it correctly
selected `tests/integration/test_interfaces.py`,
`tests/test_coverage.py`, and `tests/test_gates.py` (via a
package/file-level `frob:tests` binding) as the touched-set's python
targets, filtering out the `"*"` all-suite sentinel a `docs/`/`tickets.md`
fallback line also produced -- exactly the intended selection.

NOT built (disclosed, not silently dropped -- separate scope):
- A real background/daemon-side refresh (the ticket's option (a)). Would
  need a long-lived watcher process and its own staleness/liveness
  handling; not attempted here.
- Non-python touched-set coverage: `coverage-fast` still measures rust and
  `.strata` only via the full `make coverage` fallback path (this repo's
  `pytest-cov` only instruments the python process; rust coverage is a
  materially different toolchain (`cargo llvm-cov` or similar), out of
  this ticket's `src/frob/testing/`/`_coverage.py` scope).
- `make coverage-fast`'s shell recipe itself is not covered by an
  automated test (Make recipes are not natively unit-testable here, same
  posture as the pre-existing `coverage`/`clean` targets); its correctness
  rests on the `python_coverage_targets` unit tests below plus the manual
  verification above.
Filing no new ticket for these -- they are exactly the ticket's own
disclosed (a)/(c) alternatives and non-goals, already named in T-0484's
own body, not newly-discovered scope.

Also incidental in this diff: a same-ticket `ruff format` pass reformatted
one line in `tests/test_gates.py` that a prior sibling ticket (T-0298,
already closed) had left slightly mis-formatted -- trivial whitespace
only, no behavior change, folded into this commit rather than opened as
its own ticket.

Changed:
- src/frob/testing/_incremental_coverage.py::python_coverage_targets (new)
- src/frob/testing/__init__.py (export python_coverage_targets)
- Makefile (new `coverage-fast` target + `.PHONY` entry)
- docs/modules/testing.md (Public API section: new `frob:describes` anchor
  + prose entry for `python_coverage_targets`)
- tests/test_coverage.py (new file, 3 tests)
- tests/test_gates.py (incidental ruff-format whitespace fix, see above)

Evidence:
- tests/test_coverage.py::TestPythonCoverageTargets::test_touched_source_selects_test
- tests/test_coverage.py::TestPythonCoverageTargets::test_nothing_touched_returns_empty
- tests/test_coverage.py::TestPythonCoverageTargets::test_bad_base_ref_returns_empty

Filed: none.

Gates: `uv run pytest tests/test_coverage.py tests/test_testing.py
tests/test_gates.py -q` 210 passed. `uv run ruff check`/`uv run ruff
format --check` both clean. Plain `uv run frob check` (no `--ticket`
filter, the correct view here since T-0324/T-0298 already closed in this
same worktree -- see the playbook's stacked-ticket note): 1 new error,
REL001 ("public API changed (minor) since 0.37.0"), correctly fired --
`python_coverage_targets` is a genuine new public symbol. Discharging it
means editing `pyproject.toml`/`CHANGELOG.md`/`.frob-release.json`/
`uv.lock` via `frob release stamp`, none of which are in T-0484's scope;
per the T-0188 precedent (tickets-archive.md) this is disclosed as an open
item for the reviewer/coordinator rather than silently worked around or
self-widened into scope. `uv run frob check --ticket T-0484` (the
narrower, ticket-scoped view) additionally shows 3 SCOPE001 entries
(`docs/modules/gates.md`, `src/frob/gates/__init__.py`,
`tests/test_gates.py`) -- these are T-0324/T-0298's OWN already-committed,
already-closed changes surfacing under T-0484's narrower scope lens
because all three tickets share this one worktree/branch; they are not
new violations caused by T-0484's diff (confirmed: absent from the plain,
unfiltered `frob check` above). TEST006 (no coverage stamp -- full-suite
`make coverage` deferred to the coordinator per the playbook) and ARCH001
on `src/frob/dup/_template.py` are pre-existing and unrelated to this
ticket, same as T-0324/T-0298's Done reports.

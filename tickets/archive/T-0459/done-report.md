## Done report

Added RENDER001, a new frob.gates gate enforcing INV-RENDER-SOLE-STDOUT
(docs/modules/render.md#renderer): a command runner must reach stdout only
through frob.render.Renderer. Own module (src/frob/gates/_render_lint.py),
AST-based detection mirroring frob.gates._walk_lint's existing shape
(structurally immune to multi-line calls, aliased imports, or a string that
merely mentions `print`) -- registered into src/frob/gates/__init__.py via
additive-only edits: one import, one known-rule-id entry, one _ALL_GATES
entry, one _CANONICAL_GATE_ORDER entry, one _ProcessJob registration, one
__all__ entry. No existing gates/__init__.py logic was restructured (a
sibling agent owns src/frob/gates/** beyond this addition, per dispatch).

Detection: flags a bare `print(...)` not directed at stderr, `click.echo(
...)`, or `sys.stdout.write(...)` (any dotted/aliased form) in any
git-tracked src/frob/**/*.py file, excluding src/frob/render/ itself (the
one sanctioned home, where Renderer._emit's own print call lives). A
`file=sys.stderr` (or aliased `_sys.stderr`) keyword exempts a print --
INV-RENDER-SOLE-STDOUT governs stdout only.

Severity: WARN, not ERROR, deliberately -- straggler disclosure below.
Running the gate against this repo today finds exactly 14 bare-print call
sites across 7 files, all OUTSIDE T-0461's named runner-group list:
  - src/frob/app/check_runner.py:511,515 (the final --json/text report
    line, "printed directly ... not through the logger" by its own
    T-0202 comment -- a deliberate exception that predates this gate)
  - src/frob/app/clean_runner.py:65
  - src/frob/app/debt_runner.py:75
  - src/frob/app/doctor_runner.py:34
  - src/frob/app/gitlog_runner.py:21,23
  - src/frob/app/registry_runner.py:51,64
  - src/frob/app/test_runner.py:46,66,70,212,214
None of these are in T-0461's ticket title (graph/ticket/vet/sys/deploy/
release/outline/xref/dup/arch/docs/exports/bind/perf/mutate/stats/serve/
scaffold) -- T-0461 covered every named group cleanly (0 bare prints left
in any of them). Bumping RENDER001 to ERROR is a natural follow-up once
this list is migrated or explicitly `frob:waive RENDER001`'d; left as WARN
per the dispatch instruction ("warn-first if stragglers remain (list
them)").

Tests: tests/test_gates.py::TestRenderLintGate (3 cases: bare print fires,
src/frob/render/ package is exempt, a stderr-directed print is silent),
following the tests/test_walk_lint_gate.py fixture pattern (synthetic
tempfile git repos) since the ticket's scope names tests/test_gates.py
specifically rather than a new file.

Side-finding filed and closed as T-0562 (docs kind): T-0461's own edits to
bind/dup/mutate/perf/release/stats/sys/vet runner functions never carried a
frob:ticket edge, so COV002 fires against them once T-0461 closed (an open
ticket's scope-grace lapses on close). T-0562 added the missing
`frob:ticket` directives (comment-only, no behavior change) and is itself
now closed. Its own coverage lapses the same way once done, so `frob check
--ticket T-0459` still shows COV002/SCOPE001/REL001 noise against those
app/*.py files today -- this is a known artifact of landing three sequential
tickets (T-0461, T-0562, T-0459) in one unlanded worktree branch rather than
a T-0459 regression: none of that noise touches src/frob/gates/_render_lint.py
or the new tests/test_gates.py cases (verified directly), and it resolves
once the coordinator lands these commits onto main (the diff base shifts,
so these symbols are no longer "changed since base"). Flagging this
explicitly rather than silently declaring the branch clean.

### Changed
```
 src/frob/app/bind_runner.py    |  15 ++-
 src/frob/app/dup_runner.py     |   6 +-
 src/frob/app/mutate_runner.py  |   9 +-
 src/frob/app/perf_runner.py    |  19 ++--
 src/frob/app/release_runner.py |   9 +-
 src/frob/app/stats_runner.py   |  11 +-
 src/frob/app/sys_runner.py     |  14 ++-
 src/frob/app/vet_runner.py     |  51 +++++----
 src/frob/gates/__init__.py     |  11 ++
 src/frob/gates/_render_lint.py | 233 +++++++++++++++++++++++++++++++++++++++++
 tests/test_gates.py            |  75 +++++++++++++
 tickets.md                     | 141 ++++++++++++++++++++++++-
 12 files changed, 550 insertions(+), 44 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestRenderLintGate::test_bare_print_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_render_package_exempt` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_stderr_directed_print_is_silent` (pytest node id, verified passing when recorded)

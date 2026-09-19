---
id: T-4690
title: 'Delete every CLI alias and duplicate name: the four group verbs, fmt, docs/docs-search,
  three spellings of status, whereis'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4687
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_explore.py
- src/frob/_cli_parsers/_quality.py
- src/frob/_cli_parsers/_design.py
- src/frob/_cli_parsers/_status.py
- src/frob/_cli_parsers/_core.py
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/_cli_parsers/_verify.py
- src/frob/_cli_parsers/_shims.py
- src/frob/__main__.py
- src/frob/app/explore_runner.py
- src/frob/app/quality_runner.py
- src/frob/app/design_runner.py
- src/frob/app/status_runner.py
- src/frob/app/fmt_runner.py
- src/frob/app/docs_runner.py
- src/frob/app/doctor_runner.py
- tests/unit/test_cli_shims.py
- tests/unit/test_main_entry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/_ops.py
  reason: T-4748 holds live lease on _ops.py; will re-add once it lands
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/app/ops_runner.py
  reason: T-4748 holds live lease on _ops.py; will re-add once it lands
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 3416
  new_length: 3416
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 3416
  new_length: 3416
- mode: set
  reason: 'DOC006: a planned CLI option must not read as a cli invocation pointer
    until it exists'
  actor: logan
  at: '2026-09-19'
  old_length: 3416
  new_length: 3436
designated_repro_test: null
acceptance:
- text: Given the built argparse tree, when frob --help runs after this ticket, then
    explore, quality, design, ops, fmt, docs, whereis and the verify status / fleet
    status spellings are absent from the usage line
  evidence: []
- text: Given a deprecated spelling before its sunset date, when it is invoked, then
    it prints the surviving spelling on stderr and exits 0; given the same spelling
    after the sunset date, then it exits non-zero
  evidence: []
- text: Given git grep over .claude/ docs/ scripts/ src/ tests/ for every deleted
    name, when the sweep is re-run at close, then it returns zero hits outside the
    shim definitions themselves; the hits in ~/.claude/refs/frob.md are listed in
    the Done report instead of edited
  evidence: []
threat: null
component: cli
labels:
- cli-debloat
- points-3
anchor: false
anchor_reason: null
land_commit: null
---
POINTS: 3. Parent story T-4687. blocked_by: none (runs in parallel with T-4689).
This leaf also builds the shared deprecation-shim helper that T-4692, T-4695,
T-4696 and T-4698 all import, which is why those four are blocked on it.

OWNER DECISION: "Delete the duplicates."

MEASURED 2026-09-19. Four verb GROUPS exist that added names and removed none:
  explore  (T-1238) -> map, outline, xref, docs-search
  quality  (T-1567) -> check, test, dup, arch, bind, cycle, mutate, perf
  design   (T-1568) -> sys, registry, docs, graph, exports
  ops      (T-1569) -> release, natives, doctor, clean, fleet, deploy,
                       scaffold, gitlog, stats, process
`_cli_parsers/_explore.py::_mirror_subparser` proves the duplication literally:
it writes the FLAT parser object into the group's `choices` dict, so
`frob explore xref` and `frob xref` are the same ArgumentParser instance.
Not one of these four group verbs has ever been recorded in a kind=cli
telemetry row.

DELETE, each with a one-minor-version shim:
  - the four group verbs `explore`, `quality`, `design`, `ops` (T-4695 later
    reintroduces `explore` as a REAL verb with real leaves; this leaf removes
    the alias-mirror version and its `_mirror_subparser` machinery)
  - `fmt` -> `format` (already marked DEPRECATED, sunset 2026-12-01; finish it)
  - `docs` vs `docs-search`: keep `docs-search` as the search surface; `docs`'s
    docstring-extraction mode survives under the surviving name
  - `status` vs `verify status` vs `fleet status`: three spellings, one concept.
    Keep top-level `status` (it is the one the delta-first summary is written
    for); `verify status` and `fleet status` become shims.
  - `whereis` folded into `doctor` (frob doctor with a whereis option (planned) or a section of
    plain `frob doctor` output). `whereis` (T-4299) answers "which interpreter
    is this frob" -- that is a doctor question.

BUILD, once, for the whole story: a single shim helper (suggested home
src/frob/_cli_parsers/_shims.py) that registers a deprecated name, prints the
surviving spelling to stderr on every use, and exits non-zero once the sunset
date has passed. It MUST be expressed through the existing frob:deprecated
machinery (src/frob/gates/_debt_deprecated.py, _deprecated_baseline.py,
src/frob/app/deprecated_runner.py) and follow the `fmt` precedent in
src/frob/app/fmt_runner.py. Do NOT invent a second mechanism -- a second
deprecation path is exactly the duplication this story is deleting.

CITATION SWEEP (acceptance evidence): `git grep` every deleted name across
.claude/, docs/, scripts/, src/, tests/ and update each citation to the
surviving spelling. ~/.claude/refs/frob.md is the OWNER'S file and is OUT OF
SCOPE -- list the edits it needs in the Done report, do not touch it.

FILES (declared scope):
  src/frob/_cli_parsers/_explore.py, _quality.py, _design.py, _ops.py,
  _status.py, _core.py, _misc.py, _reporting.py, _verify.py, _shims.py (new)
  src/frob/__main__.py
  src/frob/app/explore_runner.py, quality_runner.py, design_runner.py,
  ops_runner.py, status_runner.py, fmt_runner.py, docs_runner.py,
  doctor_runner.py
  tests/unit/test_cli_shims.py (new), tests/unit/test_main_entry.py
NOTE: _core.py, _misc.py, _reporting.py and __main__.py are contended with
T-4692 and T-4695; that is why those two are blocked on this ticket rather than
declared disjoint. A frob scope is a write lease and cannot be shared.

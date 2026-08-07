## Done report

Re-measured first per instructions (uv run frob check --only invariant
--json): baseline was INV006=21, INV005=18, INV004=5, INV003=4 (total
48; my own T-0757 land's INV-042 evidence was among the INV005 18, no
INV007/INV008 turn-on findings at all).

INV005 (18 -> 0): every listed invariant's code anchor was missing a
frob:tests edge actually reaching it (existence-only evidence, per
INV001's B12 caveat). Added one frob:tests <path>::<Class.method>
directive (dotted form) at each anchor for INV-004, 006, 007, 010, 013,
015, 016, 018, 023, 025, 026, 027, 029, 030, 032, 034, 036, plus my own
INV-042 (a same-file-trust gap: the evidence test lives in a different
file than the anchor, so same-file trust never applied).

INV006 (21 -> 0): read every flagged file's actual "only"/"never"/
"always"/"exclusively" occurrence in context. All 21 (plus one new
turn-on from a concurrently-merged ticket, _deprecated_baseline.py) were
source-level design-rationale/scope-cut prose describing already-
implemented internal behavior -- not a separate cross-module contract
needing its own tracked invariant. Disposed with the SAME reasoned
frob:waive INV006 pattern this repo already established (T-0585's
first-turn-on-pool disposition), not a blanket suppression: each waiver
names the specific file and repeats the calibration-batch reasoning.
Read every occurrence before waiving; none were genuine unenforced
contracts worth inventing a fake invariant for just to clear the
detector.

INV003/INV004 (9 -> 0, 5 files): four were GENUINE, already-enforced
contracts that had simply never been anchored -- created real
invariants with real evidence and bound both the code anchor and the
doc marker:
- INV-044: .frob-release.json's version is the sole authority (REL002),
  evidence = existing tests/test_release.py::TestReleaseGateCoherence.
- INV-045: docs/modules/cli.md's generated CLI table is never
  hand-edited (DOC005 freshness), evidence = existing
  tests/test_docblocks_gate.py::TestCliCommandTableGenerator.
- INV-046: fleet.toml relative paths resolve against the manifest
  file's own directory, never cwd -- the existing test
  (test_load_manifest_ok) could not actually distinguish "manifest dir"
  from "cwd" since they coincided in that fixture, so I added a NEW
  test (test_relative_path_resolves_against_manifest_dir_not_cwd,
  tests/unit/fleet/test_manifest.py) that chdirs elsewhere first to
  close that gap honestly.
- INV-047: strata REL2xx TIMEOUT obligation (REL200/REL201), evidence =
  existing tests/unit/strata/test_reliability.py.
The fifth file (docs/modules/deploy.md) was incidental scope-cut prose
("only the windows target this ticket adds", a comment about
krb_manifest_for reuse) -- waived with a reasoned
<!-- frob:waive INV003/INV004 reason="..." --> marker, same disposition
as the code-side INV006 batch, not a fabricated invariant.

Full re-measure after all fixes (uv run frob check --only invariant,
foreground, large timeout): 0 errors, 0 warnings for gate:INV -- the
tool disappears from --json output entirely at zero findings, confirmed
against the plain-text summary too.

Mid-ticket: main advanced twice while this ticket was in flight (T-1023
landed after T-0757); each time verified via git diff main
--diff-filter=D --stat (empty both times) and re-ran the invariant gate
post-merge. The second merge brought in a concurrently-landed
_deprecated_baseline.py carrying its own fresh INV006 turn-on finding
(unrelated ticket, same file class as my batch) -- fixed with the same
established waiver pattern rather than leaving the re-measure non-zero.

No collision with T-1024 (REF001 orphan invariants) observed in
invariants/*.md during either merge.

Filed: none -- no out-of-scope work discovered.

### Changed
```
 docs/modules/cli.md                    |  2 ++
 docs/modules/deploy.md                 |  2 ++
 docs/modules/fleet.md                  |  2 ++
 docs/modules/release.md                |  1 +
 docs/strata/reliability.md             |  2 ++
 invariants/INV-044.md                  | 23 +++++++++++++++++++++++
 invariants/INV-045.md                  | 24 ++++++++++++++++++++++++
 invariants/INV-046.md                  | 23 +++++++++++++++++++++++
 invariants/INV-047.md                  | 26 ++++++++++++++++++++++++++
 src/frob/app/fleet_runner.py           |  6 ++++++
 src/frob/app/gitlog_runner.py          |  6 ++++++
 src/frob/app/mutate_runner.py          |  6 ++++++
 src/frob/arch/_concurrency.py          |  6 ++++++
 src/frob/arch/_kotlin.py               |  6 ++++++
 src/frob/arch/_normalized.py           |  4 ++++
 src/frob/arch/_patterns.py             |  6 ++++++
 src/frob/arch/_srp.py                  |  6 ++++++
 src/frob/arch/_typescript.py           |  6 ++++++
 src/frob/bind/__init__.py              |  1 +
 src/frob/deploy/_drift.py              |  6 ++++++
 src/frob/deploy/_generate_windows.py   |  6 ++++++
 src/frob/fleet/__init__.py             |  2 ++
 src/frob/gates/__init__.py             |  4 ++++
 src/frob/gates/_deprecated_baseline.py |  7 +++++++
 src/frob/gates/_docblocks.py           |  2 ++
 src/frob/gates/_protocol_summary.py    |  6 ++++++
 src/frob/gates/_ratchet.py             |  6 ++++++
 src/frob/gates/decisions.py            |  1 +
 src/frob/gitio.py                      |  6 ++++++
 src/frob/graph/_models.py              |  6 ++++++
 src/frob/graph/summary.py              |  6 ++++++
 src/frob/lang/__init__.py              |  1 +
 src/frob/logging/filter.py             |  1 +
 src/frob/perf/_recursion.py            |  1 +
 src/frob/scaffold/_managed.py          |  6 ++++++
 src/frob/scaffold/project.py           |  7 +++++++
 src/frob/serve/_daemon.py              |  6 ++++++
 src/frob/serve/_warm.py                |  6 ++++++
 src/frob/strata/_crash.py              |  1 +
 src/frob/strata/_elaborate.py          |  1 +
 src/frob/strata/_policy.py             |  1 +
 src/frob/strata/_reliability.py        |  1 +
 src/frob/strata/_selfconform.py        |  1 +
 src/frob/strata/_threat.py             |  1 +
 src/frob/strata/_waive.py              |  1 +
 src/frob/testing/_select.py            |  1 +
 src/frob/tickets/__init__.py           |  2 ++
 src/frob/tickets/_brief.py             |  6 ++++++
 src/frob/vet/_capability_modes.py      |  6 ++++++
 src/frob/vet/_scan.py                  |  1 +
 tests/unit/fleet/test_manifest.py      | 26 ++++++++++++++++++++++++++
 51 files changed, 293 insertions(+)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 10 error(s), 6470 warning(s), 358 waived
- error-findings: COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, DEPR005@tests/test_gates.py, DEPR005@tests/test_ticket_land.py, DEPR005@tests/test_vet.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py

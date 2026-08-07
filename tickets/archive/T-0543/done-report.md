## Done report

Repro: `invariant_gate`'s INV001 check was `_evidence_collected(item, tests)
or item in policy_rule_ids` -- a bare collected pytest node id with zero
edge/proximity relationship to the invariant's own `frob:invariant`-
anchored symbol satisfied it. `def test_x(): pass`, named as evidence for
any invariant anywhere in the repo, cleared INV001 regardless of whether
the test reached the anchor at all.

Fix: reused the same D-02/COV006 "binding, not existence" remedy family.
New `_invariant_anchor_symrefs`/`_evidence_binds_to_symrefs` (an analog of
`evidence_covers_scope`'s `_evidence_binds_to_scope`, but binding against
the invariant's own anchor symref set instead of a ticket's scope glob) and
`_invariant_evidence_proves_anchor` check whether a collected evidence item
is shown to reach the anchor via an either-direction `frob:tests` edge, or
same-file trust (mirroring D-02's scope-file route).

Counterexample-first: verified the OLD vacuous behavior first
(`test_inv001_passes_with_collected_evidence`'s original form used an
unrelated `tests/test_x.py::test_y` with zero relationship to the anchor
and asserted `violations == ()` -- confirming the gap existed before
touching it), then fixed it.

Calibration decision (disclosed honestly): tightening INV001 itself to
require this binding broke 17 of this repo's OWN already-adopted
invariants (`uv run frob check --ticket T-0543` showed `FAIL gate:INV 17
errors` on the first pass) -- their evidence predates any binding
convention and a legacy-adoption pass to add real `frob:tests` edges or
rebind evidence across all 17 is out of this ticket's budget, the same
"large, needs its own dedicated ticket" shape B1/B2/B6 in this same audit
family were explicitly punted on. Rather than force that mass-break (or
silently do nothing), the binding check now feeds a NEW WARN-severity
`INV005` (non-blocking, same posture as COV006's own best-effort
reachability check) instead of tightening INV001/INV002 -- both stay
ERROR, behaviorally unchanged for existing invariants. `uv run frob check
--ticket T-0543` confirms: `gate:INV 0 errors, 17 warnings` (the 17
legacy invariants now surface as an honest, visible INV005 backlog instead
of a silent pass).

Changed:
- src/frob/gates/__init__.py::_invariant_anchor_symrefs (new)
- src/frob/gates/__init__.py::_evidence_binds_to_symrefs (new)
- src/frob/gates/__init__.py::_invariant_evidence_proves_anchor (new)
- src/frob/gates/__init__.py::_inv005 (new)
- src/frob/gates/__init__.py::invariant_gate (INV005 wired in; INV001/INV002 unchanged)
- src/frob/gates/__init__.py::_KNOWN_GATE_RULES (INV005 registered)
- docs/modules/gates.md (INV005 table row + "### INV005 (T-0543)" section, matching the existing INV003/INV004 doc convention)

Evidence:
- tests/test_gates.py::TestInvariantGate::test_inv001_passes_with_collected_evidence (rewritten to a genuine same-file binding; the OLD unrelated-node-id form is now covered by the counterexample test below)
- tests/test_gates.py::TestInvariantGate::test_inv001_collected_but_unbound_evidence_warns_inv005 (the counterexample: unrelated collected evidence no longer silently proves the invariant -- INV001 stays clear, INV005 warns)
- tests/test_gates.py::TestInvariantGate::test_inv001_passes_via_explicit_tests_edge_to_anchor (positive: an explicit frob:tests edge to the anchor also satisfies the binding, no INV005)
- Full `uv run pytest tests/test_gates.py -p no:cacheprovider -q -n0`: 227 passed, 0 failed (verified before recording evidence, and re-verified after merging main); all prior TestInvariantGate/TestInv003Gate/TestInv004Gate tests unchanged and still pass.

Filed: none (the 17-invariant legacy-binding backlog is disclosed above and
visible directly via `frob check --only invariant`'s new INV005 warnings
rather than filed as a separate ticket).

Merge note: a sibling agent landed T-0546/T-0551/T-0555 to main
(0.62.0) mid-ticket; merged main in (warm-up rule, section 1 -- a
mid-ticket code merge, not a late ledger sync), resolved conflicts in
pyproject.toml/CHANGELOG.md/.frob-release.json/uv.lock (my version bump
collided in name with main's own new 0.60.0/0.61.0 registry entries --
rebased mine to 0.63.0), reran `make core`, `uv run frob release stamp`,
and the full gates test suite + `frob check --ticket T-0543` clean
post-merge. `git diff main --diff-filter=D --stat` empty (deletion-filter
land rule, section 9).

Gates: `uv run frob check --ticket T-0543` clean (0 errors, INV
0 errors/17 warnings as expected). No public API signature change
(`invariant_gate`'s signature is unchanged; `_inv005` and the new helpers
are private) -- but a version bump was still needed to reconcile with
main's already-advanced 0.62.0 (see merge note); pyproject.toml now 0.63.0,
CHANGELOG.md/`.frob-release.json`/`uv.lock` refreshed to match. Scope
widened via `frob ticket scope --add` for docs/modules/gates.md
(doc-as-you-go for the new gate) and for pyproject.toml/CHANGELOG.md/
.frob-release.json/frob.lock/uv.lock -- these keep showing as SCOPE001
hits because the T-0108 cross-ticket commit-subject exemption needs a
`T-####` reference in the COVERING commit's subject line, which T-0541's
and T-0542's commit subjects omitted; scoped directly here rather than
rewriting already-committed history. tests/test_gates.py stays under
T-0541's pre-existing SCOPE001 waiver (T-0160 holds the tests/** lease);
touched test symbols in that file now carry `frob:ticket T-0543` alongside
the prior tickets' tags for the same reason (T-0541/T-0542 are DONE and no
longer "open", so their edges alone no longer satisfy COV002 for symbols
still sitting in this same uncommitted-to-main working diff).

### Changed
```
 CHANGELOG.md               |  13 +++
 docs/modules/gates.md      |  25 +++++
 frob.lock                  |   2 +-
 pyproject.toml             |   2 +-
 src/frob/gates/__init__.py | 260 ++++++++++++++++++++++++++++++++++++++++++---
 tests/test_gates.py        | 229 ++++++++++++++++++++++++++++++++++++++-
 uv.lock                    |   2 +-
 7 files changed, 511 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInvariantGate::test_inv001_collected_but_unbound_evidence_warns_inv005` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantGate::test_inv001_passes_via_explicit_tests_edge_to_anchor` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantGate::test_inv001_passes_with_collected_evidence` (pytest node id, verified passing when recorded)

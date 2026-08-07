## Done report

Changed:
- src/frob/gates/__init__.py::_edges_of_kind (new shared helper)
- src/frob/gates/_debt_deprecated.py::_debt_edges, _deprecated_edges
- src/frob/gates/_waive.py::_waive_edges
- src/frob/gates/_design_invariants.py::_establishes_claims

Re-measured `uv run frob check --only arch --json` scoped to
src/frob/gates/ per the ticket's own instruction (T-1115's split had
shifted line numbers but not the finding count: still 29). Read every
group's actual member bodies (T-1112's triage style) rather than
counting by signature alone:

One real, bounded extraction was made: `_debt_edges` (T-1115's new
`_debt_deprecated.py`), `_deprecated_edges` (same file), and
`_waive_edges` (`_waive.py`) were three BYTE-IDENTICAL one-line bodies
(`tuple(e for e in snapshot.edges if e.kind == EdgeKind.X)`), not just a
coincidental signature match -- consolidated behind one new
`frob.gates._edges_of_kind(snapshot, kind)` helper, called back via a
call-time import from each submodule (same lazy-import shape
`_site_from_edge_origin`/`_OPEN_STATES` already establish for shared
__init__.py helpers used by split-out submodules). `_establishes_claims`
(`_design_invariants.py`) also now reuses `_edges_of_kind` for its base
kind-filter, narrowed further by its own `establishes=` attribute check
-- distinct logic, not force-merged into the identical-body group.

NOTE ON ATTRIBUTION: this fix was committed as a checkpoint alongside
T-1114's own work in this worktree, and by the time it was ready to
land, `frob ticket land T-1115` picked up the whole worktree diff and
landed it as PART OF T-1115's commit (fc1861b7 on main) rather than a
separate T-1114 commit -- confirmed via `git show fc1861b7 --stat`
showing `_debt_deprecated.py`/`_waive.py`/`_design_invariants.py` in
that same commit. The code is real and on main; it is just not under a
distinct T-1114 commit hash. Recorded here for an honest paper trail.

The ARCH gate's abstraction-opportunity detector is signature-shape-
only, not body-based (confirmed: re-running `--only arch --json` after
the fix still reports the same 4-member group, since the detector
cannot see that 3 of the 4 now delegate to a shared helper) -- so the
detector's own count does not change, and chasing it further via code
changes is not productive without a detector fix.

Of the remaining 28 (or still-29-by-the-detector's-count) findings, the
overwhelming majority are the gate-rule-builder protocol family itself
(every gate/rule function in gates/__init__.py sharing one of a handful
of `(...) -> Violation`/`(...) -> tuple[Violation, ...]`/
`(...) -> list[Violation]` shapes by design -- the package's own common
interface, not duplication), plus a handful of small genuinely-
coincidental utility collisions (_baseline.py's config loaders,
_gate_cache.py's readonly/readwrite sqlite openers, _waive_lease.py's
lease operations, _pii_structural/_env_access.py's ast predicates) --
the same "protocol family" and "coincidental tree-walk shape" categories
T-1112 already established for src/frob/arch/**'s own detector.

Filed T-1141 (generalizes T-1112's exclusion mechanism to
cover a package's own gate/rule-builder convention, scoped to
src/frob/arch/** where the detector itself lives; final id verified on
main after renumbering at land).

Evidence: tests/test_gates.py::TestDebtGate::test_debt001_malformed_directive_is_reported,
tests/unit/test_design_invariants.py (Inv007/Inv008 classes),
tests/test_waive_gate.py -- full targeted run: all pass (confirmed
after natives rebuild + main merge).

Gates: `uv run frob check --ticket T-1114 --only gates-fast` clean of
anything this ticket's diff introduced (the sole COV001 remains the
same pre-existing, out-of-scope `_tracked_files.py::tracked_files`
finding already disclosed in T-1115's Done report). No threshold
loosening; no waiver added by this ticket's own diff (the 3 functions
touched needed only a body change, no new gate-affecting directive).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDebtGate::test_debt001_malformed_directive_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_depr001_malformed_directive_is_reported` (pytest node id, verified passing when recorded)
- `tests/unit/test_design_invariants.py::TestInv007::test_forbidden_import_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_pending_phrasing_is_binding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

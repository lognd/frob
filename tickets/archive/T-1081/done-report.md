## Done report

Split src/frob/gates/_waive.py (2060 lines, unwaived ARCH102 god-module:
35 top-level exports across 4 unrelated naming/usage clusters) into
three cohesive modules, removing the T-1072 transitional ARCH102 waiver
entirely (no waiver anywhere in the module now):

- src/frob/gates/_waive.py (1374 lines): WAIVE001-005/DSL001 directive
  validation, the rule-id registry (_KNOWN_GATE_RULES/known_gate_rule_ids/
  _UNWAIVABLE_RULES), and the shared _match_waiver/_apply_waivers/
  _ceiling_ok/_severity_overrides matching spine every other gate's
  violation list is filtered through -- one cluster: validating and
  applying `frob:waive` directives.
- src/frob/gates/_waive_comments.py (new, 625 lines): WAIVE006/007 (stale/
  dangling waiver ticket refs, both the frob:waive comment channel and the
  .strata waive clause channel) and PLACE001 (misplaced frob: directive) --
  one cluster: is a directive COMMENT sitting somewhere sound.
- src/frob/gates/_waive_lease.py (new, 103 lines): active_ticket/
  ticket_lease_pin -- the --ticket resolution and cross-worktree
  lease-pin helpers that rode along in T-1072's original extraction but
  have nothing to do with waiver matching at all.

Every frob:ticket/frob:tests/frob:enforces/frob:doc directive moved
verbatim with its function. _waive_comments.py imports _waive_edges back
from _waive.py (a real, non-circular dependency -- _waive.py never
imports _waive_comments); _site_from_edge_origin/_design_dir stay
lazily imported from frob.gates at call time inside the moved functions,
same posture T-1072 established.

src/frob/gates/__init__.py's single `from frob.gates._waive import (...)`
block split into three import statements (from _waive, _waive_comments,
_waive_lease respectively) -- every re-exported name unchanged, verified
via `import frob.gates` succeeding and the full gates test suite passing.

DRIFT002 path fixups (4 stale directives found via repo-wide grep,
mechanical module-path-only edits, no semantic change):
tests/test_gates.py::TestActiveTicket.test_explicit_flag_wins
(frob:tests _waive.py -> _waive_lease.py), and 3 docs/modules/gates.md
frob:describes anchors (_place001_missed_symbol, _place001_bindings ->
_waive_comments.py; active_ticket -> _waive_lease.py).

Post-merge follow-on fix (found while merging main forward mid-ticket,
fixed in this land per playbook guidance rather than deferred): main
landed T-0668 (SYS104/105/106, src/frob/strata/_selfconform.py) after
this ticket's own _waive.py split diverged, and _KNOWN_GATE_RULES (which
lives in this ticket's own scope file) was missing all three ids --
TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known failed
post-merge. Added SYS104/105/106 to the literal, same "generated_gate_
rule_ids reports it, paste it in" discipline the literal's own T-0966
comment documents.

git diff main --diff-filter=D --stat: empty (no unintended deletions).
tests/test_gates.py + test_secrets_gate.py + test_waive_gate.py: 559
passed.
frob check --ticket T-1081 --only arch: 0 errors; grep-confirmed
_waive.py no longer appears in ANY god-module finding (ARCH102 cleared);
_waive_comments.py/_waive_lease.py trip no new god-module/large-file
finding of their own. 17 pre-existing warnings + 231 suggestions, none
new to this change (spot-checked: no _waive_comments.py/_waive_lease.py
entries).
frob check --ticket T-1081 --only drift/--only test: 0 errors both runs.

### Changed
```
 docs/modules/gates.md             |   6 +-
 src/frob/gates/__init__.py        |   9 +-
 src/frob/gates/_waive.py          | 726 +-------------------------------------
 src/frob/gates/_waive_comments.py | 627 ++++++++++++++++++++++++++++++++
 src/frob/gates/_waive_lease.py    | 103 ++++++
 tests/test_gates.py               |   2 +-
 tickets.md                        |  17 +-
 7 files changed, 771 insertions(+), 719 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_ticket_attr_bound_to_done_ticket_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_unresolvable_id_fires` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_unresolvable_id_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestActiveTicket::test_explicit_flag_wins` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

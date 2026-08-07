## Done report

Removed the stale .kt/.kts entries from LANG002's
_UNREGISTERED_CANDIDATE_LANGUAGES dict in src/frob/gates/_lang_conformance.py:
kotlin gained a real frob.lang grammar registration in T-0723, so leaving it
in the "no grammar exists at all" candidate set was a latent false-ERROR
waiting to fire on any downstream repo with .kt/.kts files, even though this
repo's own tree never tripped it. Added a comment explaining the T-0723
registration and the removal rationale so a future language added to the set
is pulled out the same way once it gains real frob.lang registration.
Extended tests/test_lang_conformance_gate.py with
test_kotlin_file_no_longer_flagged_by_lang002 (a still-registered kotlin file
passes LANG002 cleanly) and reworked the still-unregistered-language case to
use a language other than kotlin per the ticket's scope_changes note.

### Changed
```
 design/frob.strata                              |   4 +
 docs/commands/gitlog.md                         |   1 +
 docs/guides/agent-playbook.md                   |   1 +
 docs/guides/extending/comment-dsl-directives.md |   6 +-
 docs/guides/extending/sys-export-formats.md     |   1 +
 docs/guides/extending/ticket-kinds-states.md    |   2 +
 docs/modules/gates.md                           |  27 +++
 docs/modules/graph.md                           |  12 +-
 src/frob/gates/__init__.py                      |   6 +
 src/frob/gates/_docenum.py                      | 301 ++++++++++++++++++++++++
 src/frob/gates/_lang_conformance.py             |  16 +-
 src/frob/gates/_waive.py                        |   3 +
 src/frob/graph/_models.py                       |  12 +
 src/frob/graph/dsl.py                           |  55 +++--
 tests/test_docenum_gate.py                      | 116 +++++++++
 tests/test_graph.py                             |  34 +++
 tests/test_lang_conformance_gate.py             |  28 ++-
 tickets.md                                      | 160 ++++++++++++-
 18 files changed, 757 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_kotlin_file_no_longer_flagged_by_lang002` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 342 warning(s), 679 waived
- error-findings: OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py

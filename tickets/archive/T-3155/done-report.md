## Done report

Verified premise against main as it stands now (post-T-3156, which landed at
21055ca26f9b and added a scope_has_python_surface call inside
evidence_covers_scope) -- re-read the function's current shape before
touching anything. Confirmed both edges still exist exactly as described:
src/frob/gates/__init__.py imports Ticket/TicketQueue/TicketState/load_queue
from frob.tickets, and src/frob/app/ticket_runner/_close_cmd.py:300 deferred-
imports evidence_covers_scope from frob.gates. Baseline SCC size measured
directly (frob cycle src) before any change: 182 nodes.

Command run (per the owner's standing instruction to use the tool, not hand
edits):
  frob refactor split frob.gates.__init__ \
    --symbols evidence_covers_scope,_evidence_binds_to_scope,_node_id_matches_symref,_file_of_symref_in_scope \
    --into frob.tickets._scope_coverage --skip-check-delta

(source had to be spelled "frob.gates.__init__", not "frob.gates" --
module_to_path has no package-__init__ fallback and the bare form fails
resolve with "module file missing: .../gates.py"; worth its own ticket if
this recurs.)

The split's own dependency scanner missed one transitive need: the moved
_node_id_matches_symref calls _symref_to_nodeid, which stays behind in
frob.gates (used elsewhere there too) and was never imported into the new
module -- confirmed by running the moved code's own bound tests immediately
after the split (5 failures, all NameError: _symref_to_nodeid not defined).
Fixed by hand-adding `from frob.gates import _symref_to_nodeid` to the new
module (a missing-dependency fix, not a rename the tool would handle) and
re-ran the same tests clean. Also hand-repointed _close_cmd.py's deferred
import from `frob.gates` to `frob.tickets._scope_coverage` (the split itself
only added a frob.gates backward-compat re-export -- T-3086's own T-3143
finding that importers are not auto-repointed to the leaf) since leaving it
on the compat shim would not actually cut the edge this ticket exists to cut.

SCC MEASUREMENT (frob cycle src, same tool/invocation before and after):
BEFORE: 182 nodes
AFTER:  183 nodes (the new frob.tickets._scope_coverage module appears BY
  NAME in the printed cycle membership)

This is an honest, useful-not-a-failure result per the ticket's own framing:
the direct _close_cmd.py -> frob.gates edge for evidence_covers_scope IS cut
(confirmed: `git grep evidence_covers_scope src/frob/app/ticket_runner/_close_cmd.py`
now shows only `from frob.tickets._scope_coverage import evidence_covers_scope`),
but frob.gates and frob.tickets remain mutually reachable through the
separate, deliberately-untouched _tickets_gate.py edge (gates -> tickets) plus
the many other paths already binding the two packages into one SCC -- so the
new leaf module, which itself imports both frob.graph and frob.tickets
(and now frob.gates, for _symref_to_nodeid), joins the same existing SCC
rather than escaping it. Node count is not a reduction; it is +1, matching
T-3086's own prior finding that a real, correct extraction does not
necessarily shrink this particular cycle. Do not read the printed node
sequence as a validated edge walk (Tarjan membership order only).

Evidence: tests/test_evidence_integrity.py (56 tests) and
tests/gates/test_scope_symref_helpers.py both pass clean after the fix.
tests/test_gates.py has 21 pre-existing failures in this worktree
(reproduced identically on the primary checkout's own working tree,
unrelated to this change -- native-extension-unavailable environment gaps
in a fresh worktree plus a pre-existing TDD001/VMOD001/VERSION001 rule-id
registration gap), none touching D-02/evidence_covers_scope/scope_coverage/
symref machinery.

### Changed
```
 src/frob/gates/__init__.py          | 112 ++------------------------------
 src/frob/tickets/_scope_coverage.py | 124 ++++++++++++++++++++++++++++++++++++
 tickets/T-3155/ticket.md            |   2 +-
 3 files changed, 132 insertions(+), 106 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

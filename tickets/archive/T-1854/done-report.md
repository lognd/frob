## Done report

Routed frob refactor rename's per-ticket structured-evidence node-id
citation rewrite through frob.tickets.replace_evidence's audited path
instead of a raw text substitution, closing the T-1546 follow-up
asymmetry (T-1733's EvidenceChangeEntry existed for a manual --replace
but not for this automated carrier).

Design, kept inside the declared two-file scope (no _apply.py/_models.py
change): scan_evidence_citations (src/frob/refactor/_repointer.py) still
returns a RewriteOp for every hit unchanged -- dry-run preview is
unaffected. A new apply-phase step in _transaction.py,
_route_evidence_rebinds_through_replace_evidence, runs in run_refactor
BEFORE apply_plan: it recomputes the exact old/new pytest node-id pair
(via a new small helper, _evidence_citation_targets, split out of
scan_evidence_citations so both call sites share one computation), finds
which of plan.reference_ops target a per-ticket tickets/<id>/ticket.md
file citing that node id (via another new helper,
_ticket_id_from_ledger_path), and for each: calls replace_evidence with
a reason derived from the refactor operation itself
("carried by frob refactor rename: <old> -> <new>"). On success the op
is dropped from the plan handed to apply_plan (already written, audited,
captured by the same git add -A WIP commit regardless of which mechanism
wrote it). On replace_evidence's own refusal (most commonly
EvidenceReplaceNotFound -- the hit was free prose, not a real structured
evidence/acceptance binding) the op is left UNCHANGED for the pre-existing
raw-text apply path -- never a silently dropped rewrite.

Both new helpers ended up PRIVATE (not exported), not public as first
drafted: making them public required declaring them in design/frob.strata's
refactor node interface= list, which is currently held by T-1870's live
in-progress lease (confirmed via .git/frob-leases -- my own T-1868 fix
correctly refused the scope-add). Kept private and imported directly
across the module boundary within the same frob.refactor package instead
-- the same precedent _display_path's own docstring already documents in
this file -- avoiding the contended file entirely rather than waiting on
it or forcing the lease.

Found and filed separately (not fixed here, out of the declared two-file
scope): src/frob/refactor/_verify.py's verify_import_resolution
ast.parses every touched file with no .py extension filter -- any
reference_ops entry touching a non-Python file (a ticket.md evidence
citation, a registry yaml) makes run_refactor's Verify phase fail and
roll back the whole transaction, even though the rewrite itself was
correct. This means the pre-existing T-1546 evidence carrier and T-1200
registry carrier were ALREADY silently non-functional through the real
end-to-end run_refactor path (confirmed by reproduction: a ticket
carrying a real evidence citation for a moving symbol rolled back).
Filed T-1885. My own regression tests for this ticket call
_route_evidence_rebinds_through_replace_evidence directly against a real
build_plan output rather than through run_refactor, to test the routing
behavior in isolation from that pre-existing, unrelated gap.

Filed: T-1885 (verify_import_resolution Python-extension filter gap).

### Changed
```
 tickets/T-1617/ticket.md           |  9 +++++--
 tickets/T-1854/ticket.md           | 39 ++++++++++++++++++++++++++++-
 tickets/T-1885/ticket.md | 51 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 96 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 789 warning(s), 742 waived
- error-findings: none (measured, zero errors)

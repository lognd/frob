## Done report

Added `fix_cov002_ticket_directive_insertion` to `src/frob/gates/_fix_engine.py`,
registered as `TIER_A_HANDLERS["COV002"]`. It inserts `# frob:ticket
<landing-id>` (or `//` for a `.rs` source) directly above a symbol COV002
flags as changed-with-no-coverage, but ONLY when the caller supplies a
real, currently OPEN `ticket_id` and the finding is against `working_diff
(root, "main")` -- this land's own diff, the only diff the handler has
any basis to attribute a fix to. A `ticket_id` of `None` (bare `frob check
--fix` outside a land) is a whole-handler no-op.

This handler needed the landing ticket id, which no other Tier-A handler
does -- `TIER_A_HANDLERS`'s callable shape and `apply_tier_a_fixes`'s own
signature both grew a `ticket_id: str | None = None` parameter (backward
compatible; every existing handler ignores it). `src/frob/app/
ticket_runner/_land_cmd.py`'s two `apply_tier_a_fixes` call sites
(`_tier_a_pre_land_step`, `_apply_root_tier_a_fixes`) now pass their own
`ticket_id` argument through -- both already had it, per the ticket's own
plan. Scope was widened to include this file
(`frob ticket scope T-1548 --add`, both call sites were `queued`, not
leased).

<!-- frob:waive DOC006 reason="historical Done report: docs/modules/gates_e501_autofix.md was real when this landed; T-1580's own follow-up (also in this ledger) later folded it into gates.md and deleted it" -->
Doc note: same T-1205 lease situation as T-1547 (worked in this same
worktree) -- `docs/modules/gates_e501_autofix.md` (T-1547's own
standalone page, since renamed in spirit to a shared "pending fold-in"
page) now also carries this handler's writeup, with the same disclosed
follow-up (T-1580, already filed by T-1547) to fold both
sections into `docs/modules/gates.md` once T-1205's lease clears.

Residue at `frob check --ticket T-1548`: 4 SELFAUDIT001 findings (SYS100
exec-capability for the test module + 3x SYS104 undeclared-public-symbol
for `fix_cov002_ticket_directive_insertion`/`fix_e501_merge_introduced`/
the two new test classes) against `design/frob.strata` -- expected to
self-heal via `frob ticket land`'s own pre-land
`fix_sys100_may_via_union`/`fix_sys104_interface_union` Tier-A handlers
(same T-1531 precedent noted in T-1547's Done report); `design/frob.strata`
sits under an in-progress T-1220 lease so I could not hand-edit it. 4
pre-existing TICK006 findings (T-1238 phantom draft citations) are
unrelated repo-wide debt, not introduced by this ticket.

Gates: `frob check --ticket T-1548` -- 0 SCOPE/PRE/COV/DOC/WIRE/FMT
errors after two fix-forward passes (an initial run caught a stale doc
anchor slug and a WIRE001 finding on the bare function reference in
`TIER_A_HANDLERS`, both fixed: the doc anchor slug corrected, the dict
entry wrapped in a calling lambda matching every sibling handler's own
shape). The 4 SELFAUDIT001 + 4 TICK006 residue above are the only
remaining errors, both disclosed and out of this ticket's own reach
(lease conflict / land-time self-heal / pre-existing debt).

### Changed
```
 docs/modules/gates_e501_autofix.md |  43 ++++++++++++
 src/frob/gates/_fix_engine.py      | 139 ++++++++++++++++++++++++++++++++++++
 tests/test_gates_fix_engine.py     |  94 +++++++++++++++++++++++++
 tickets.md                         | 140 ++++++++++++++++++++++++++++++++++++-
 4 files changed, 413 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_gates_fix_engine.py::TestFixCov002TicketDirectiveInsertion::test_open_landing_ticket_gets_directive_inserted_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFixCov002TicketDirectiveInsertion::test_no_ticket_id_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 385 warning(s), 786 waived
- error-findings: none (measured, zero errors)

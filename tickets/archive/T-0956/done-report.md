## Done report

Re-expressed the five SYS203/tickets_ledger waivers' underlying arbitration
claim (cli/gates/fleet/core/serve) using T-0700's grammar: a new top-level
`resource tickets_ledger { lock "tickets.lock"; }` declaration plus an
`access "tickets_ledger" mode write;` clause on each of the five writer
nodes. Verified directly against frob's own elaborated design (parse ->
elaborate -> frob.strata._access.resource_contention_violations(model,
module)): zero SYS204 violations for tickets_ledger -- the declared lock
discharges every conflicting write/write pair among the five accessors.

The SYS203 waivers themselves were NOT dropped, contrary to the ticket's
literal "drop the now-superseded SYS203 waivers" framing: SYS203
(src/frob/strata/_contention.py::check_resource_contention) is a
completely separate, permanently mode-blind check with no code path that
reads Module.resources/access attrs at all (confirmed by reading the
module: "no grammar change", counts ANY inbound Flow to a store as a
write). Adding resource/access data cannot make SYS203 stop firing --
only a src/frob/strata/_contention.py code change could, and that file is
out of this docs-only ticket's declared scope (design/**, tests/
test_tickets_live_tracker.py). Removing the waivers without a code change
would just turn 5 clean gates red for no reason. Instead, each waiver's
reason text was rewritten to state this precisely (SYS203 is structurally
blind to the now-modeled arbiter, not that arbitration is unproven), and
the forward-looking "re-evaluate at T-0700"/"drop this waiver, tracked by
T-0956" language was retired since T-0956 is itself the re-evaluation.
docs/strata/roadmap.md's self-hosting-commitments-decision-d7 section
(AFFECT001's closure doc for the five changed nodes) was updated to match,
and scope-added since it was outside the ticket's original declared
scope.

tests/test_tickets_live_tracker.py:220's "T-0700 placeholder" the ticket
plan referenced no longer exists in the current test file (grepped for
both "T-0700" and "placeholder" -- zero matches) -- already resolved by
an earlier, unrelated change to that test file before this ticket was
actioned; no edit was needed there.

Evidence: tests/unit/strata/test_selfconform.py (self-conformance stays
green with the new resource/access clauses), tests/unit/strata/
test_access.py (SYS204 machinery itself, TestResourceContentionViolations
covers arbitrated_by/lock discharge), tests/unit/strata/test_contention.py
(confirms SYS203 still fires independent of the new grammar, proving the
"separate mode-blind check" claim), tests/system/test_frob_self_model.py
(frob's own design stays self-conformant + zero SYS violations post-edit).
All re-run clean after the design/frob.strata + roadmap.md changes.

Gates: `frob check --ticket T-0956 --only gates-fast --only gates-native`
clean (0 errors both groups) after: (1) fixing AFFECT001 by updating and
scope-adding docs/strata/roadmap.md, (2) refreshing the pre-work sweep
(frob ticket sweep T-0956) to clear stale PRE001.

Filed: T-1025 -- "strata SYS203: make shared-store-write
contention consult a resource's declared arbiter, drop tickets_ledger
waivers" (feature; scope src/frob/strata/_contention.py, tests/unit/
strata/test_contention.py, docs/strata/host.md, design/frob.strata,
tickets.md). The five SYS203:tickets_ledger waivers' `ticket=` citation
was re-pointed from T-0956 to this successor draft id so T-0956 can close
cleanly (frob's live-tracker check refuses to close a ticket still cited
by a live waiver) -- the successor is the actual code-level follow-up
that would let SYS203 itself, not just SYS204, discharge the arbiter and
let the waivers finally be dropped.

### Changed
```
 design/frob.strata     | 106 ++++++++++++++++++++++++++++++++++++-------------
 docs/strata/roadmap.md |  26 ++++++++----
 tickets.md             |  80 ++++++++++++++++++++++++++++++++++++-
 3 files changed, 175 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_arbitrated_by_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestResourceContentionViolations::test_lock_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_two_writers_fires_mode_blind` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 4929 warning(s), 333 waived
- error-findings: none (measured, zero errors)

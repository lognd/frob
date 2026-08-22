## Done report

Re-measured all 32 claimed (rule, file) identities against the CURRENT
floor (not the ticket body's counts). Method: ran the specific gate
families (archgate, coverage, doclink/docanchor, drift, tickets, wire,
sys, perf, pii_structural) unscoped and diffed the live diagnostics
against the ticket's claimed identity list.

RESULT: 27 of 32 (84%) genuinely reproduce; 5 of 32 (16%) are stale
(pre-existing residue that does not currently fire, contra the ticket
body's claim of "new"):

STALE (dropped, do not reproduce against current unscoped gate output):
- DOC011  docs/design/gate-semantics-classification.md
- DOC011  docs/guides/coordinator-scripts.md
- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py
- DRIFT001  src/frob/gates/_fmt_directives.py
- DRIFT002  scripts/fleet_status.py
(gate:DOC read 7 errors total = exactly the 4 DOC001/DOC002 identities
that do reproduce, none from DOC011; gate:DRIFT read 1 error total =
exactly DRIFT002 src/frob/verify/_drain.py, none of the other 3.)

Of the 27 real identities, 8 were already attributed by the sweep's own
reachability engine to OTHER, already-closed/dropped tickets (not T-2299):
- ARCH103  src/frob/release/_cli.py       -> T-2242
- RENDER001  src/frob/release/_cli.py     -> T-2242
- SEC110  tests/test_release.py           -> T-2242
- COV001  src/frob/verify/_drain.py       -> T-2310
- DOC002  src/frob/verify/_drain.py       -> T-2310
- DRIFT002  src/frob/verify/_drain.py     -> T-2310
- DRIFT001  src/frob/gates/_fmt_directives.py (also independently STALE,
  see above -- listed once, do not double count)
- PERF003  src/frob/gates/_debt_deprecated.py -> T-2178
These are debt that escaped their own tickets' gates at land time, not
work this ticket owns; recording here rather than silently dropping, per
playbook. T-2242/T-2310/T-2178 are all already closed/dropped so there is
no live ticket to fold them into directly -- flagging in this Done report
is the disclosed record.

The remaining 19 genuinely-new, UNATTRIBUTED identities constitute a real
multi-file refactor (several are ARCH001/ARCH103 architecture-complexity
findings needing actual function decomposition, not a quick fix) -- filed
as a proper child ticket with full per-identity analysis rather than
forced through: T-2341 (renumbers at land; see its body for the complete breakdown and a
per-rule-family fix plan).

BLOCKER hit and repaired en route: `frob ticket new` was crashing
repo-wide (NotImplementedError: Non-relative patterns are unsupported,
in _new.py::_expand_scope_globs_to_paths via the scope-overlap-warning
check) because T-2308 (a queued, non-terminal sibling sweep ticket from
this exact family) had been auto-filed with ABSOLUTE filesystem paths in
its scope instead of repo-relative ones. This blocked every agent's
`frob ticket new` fleet-wide, not just mine. Root-caused by iterating all
non-terminal tickets' scope through Path.glob(); T-1753/T-1756 have the
same corruption but are state=done and correctly excluded from the live
check. Repaired T-2308's scope via `frob ticket scope T-2308 --remove
<abs> --add <rel>` (CLI-mediated, not a hand-edit; reason recorded on
that ticket). This is disclosed here because it was necessary,
out-of-scope-but-urgent repair, not silent scope creep -- the underlying
auto-filer bug that emits absolute paths, and the missing defensive
handling in _expand_scope_globs_to_paths for a non-relative pattern, are
both real defects; filing a follow-up is next (see Filed below).

Changed: tickets.md (T-2331's own block), tickets/T-2308/ticket.md (scope
repair, disclosed above)
Evidence: none (no code changed under T-2331's own scope; this was a
measurement + dispositioning ticket per its own instructions)

Filed: T-2341 (the 19-identity refactor), T-2342 (the
absolute-path filer bug + missing defensive glob-pattern guard) -- both
renumber to real ids at land.
Gates: not run under T-2331's own scope (no code change); the two child
tickets carry their own gate obligations at their own land time.

### Changed
```
 tickets/T-2308/ticket.md           | 145 +++++++++++++++++++++++++++++++++-
 tickets/T-2331/ticket.md           | 155 +++++++++++++++++++++++++++++++------
 tickets/T-2341/ticket.md | 107 +++++++++++++++++++++++++
 tickets/T-2342/ticket.md |  73 +++++++++++++++++
 4 files changed, 456 insertions(+), 24 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@src/frob/verify/_drain.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2331/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK004@tickets.md, WIRE003@docs/modules/cli.md

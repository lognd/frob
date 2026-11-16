# Obligation

Status: current
Owner: frob
Decisions: none
Audience: user

An obligation is something the repository owes before a change is
finished: a ticket bound to the code it touches, a test covering a
public symbol, a doc acknowledged after the code it describes drifted,
a changelog entry, and so on. The obligation graph is the set of those
links, built from the code model and the comment directives
(`frob:ticket`, `frob:tests`, `frob:doc`, `frob:invariant`,
`frob:todo`, `frob:waive`), the ticket ledger, leases, acks and the
docs. An obligation is open until the link that discharges it exists.

`frob check` evaluates the graph and reports each unmet obligation as a
finding of a rule, exiting 1 at or above `fail_on`. Rule families
include DRIFT (doc drift), COV and TEST (coverage), SCOPE (lease
scope), TODO, DOC, INV, and POL (user policy via `[[policy]]` in
`frob.toml`).

Where the rules live:

- The accounting rule families are implemented in the
  `frob-obligations` crate.
- Each rule has a reference page in `docs/reference/rules/`; print one
  offline with `frob explain <RULE>`.
- Rule files (`rules/ID.grl`) are managed with `frob rule`
  (`test`, `check`, `why`, `new`).
- Directive syntax is in `docs/reference/directives.md`.

An obligation is discharged by satisfying it, or excepted with a
reasoned `frob:waive`; `frob dismiss` records a finding as dismissed
in the precision history.

See also: [ticket lease](ticket-lease.md), [cycle](cycle.md).

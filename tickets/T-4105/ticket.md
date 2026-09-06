---
id: T-4105
title: the --base flag is dropped by every nested frob check spawn, so off-main ticket
  work is judged against main by all diff-driven gates
state: queued
kind: bug
origin: agent
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a ticket branched off a non-main target branch and an explicit base
    naming it, when close or land spawns its nested frob check, then that child judges
    the diff against the named base rather than main
  evidence: []
- text: given no base supplied anywhere, when a nested check spawns, then its behaviour
    is identical to today
  evidence: []
- text: given a top-level check_base default in frob.toml, when a nested check spawns,
    then that default still applies and an explicit flag overrides it
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE CLI `--base` FLAG IS DROPPED BY EVERY NESTED `frob check` SPAWN, so a ticket
developed against a non-main target branch has all diff-driven gates judged
against main. Reported as logand.app-v2 F-304: T-0264's agent passed a --base
naming their feature branch, and gate:COV still reported 32 COV002 findings on a
file the ticket did touch, judged against a base 816 commits stale.

I MEASURED THE PLUMBING BEFORE FILING, because the obvious reading -- "--base is
only wired to gate:SCOPE" -- is WRONG on main today, and filing it that way would
have sent an implementer at the wrong module:

  - the flag parses into check_base (frob/_cli_parsers/_check.py:98)
  - check_runner.py:1345 folds it into the GateConfig base, defaulting to main
  - gates/__init__.py:6602 loads the working diff from that base
  - the COV002 branch at gates/__init__.py:1288 consumes exactly that diff

So a DIRECT `frob check --base <branch>` does honour the flag for the
diff-driven gates. The defect is one layer out.

THE ACTUAL MECHANISM: SIX SITES SPAWN A CHILD `frob check`, AND NOT ONE PASSES
`--base` THROUGH. The child re-parses argv from scratch, finds no base, and
falls back to main:

    app/ticket_runner/_close_cmd.py:454      close's gates spawn
    app/ticket_runner/_close_cmd.py:833      close's second gates spawn
    app/ticket_runner/_land_cmd.py:651       the post-land sweep argv builder
    app/ticket_runner/_land_cmd.py:3576      land's tickets-gate guard
    app/ticket_runner/_rapid_sweep.py:1606   the rapid sweep
    app/ticket_runner/_verify.py:1056        verify's per-ticket check

Every one of those forwards other scoping (--only, --ticket, --budget, --json)
and drops this one. That is the producer/validator desync shape: the parent knows
the base and the child, which does the judging, is never told.

WHY IT MATTERS NOW RATHER THAN AS BACKLOG. T-3787 JUST LANDED support for landing
onto a non-main target branch, explicitly to unblock off-main v1.0.0 development.
That feature is what makes this reachable, and the first consumer to use an
off-main workflow hit it immediately. Shipping the ability to work off main while
every nested gate still measures against main means the gates are wrong for
exactly the workflow we just enabled -- and wrong in the silent direction: the
findings LOOK like real coverage gaps on files the ticket touched, so an agent's
cheapest response is to add waivers or churn the file. That is the
wrong-incentive class: the cheapest way to clear the gate degrades the code.

ONE MITIGATION ALREADY EXISTS AND SHOULD BE STATED IN THE FIX, not left for the
next reader to discover: the child re-reads frob.toml, and check_runner.py:69
picks up a top-level check_base key from it. So a repo-wide default DOES reach
the nested spawns; only the per-invocation CLI flag is lost. That asymmetry is
itself a trap -- a flag that works at the top level and silently does nothing one
process deeper -- so fixing the forwarding matters even though a workaround
exists.

WHAT TO DO
  1. Forward the effective base to every nested spawn. Prefer threading it as an
     explicit argument over an environment variable: an env var is invisible at
     the call site and leaks into unrelated children.
  2. Find the spawn sites by construction, not by this list. I found six by
     grepping the argv literals; treat that as a lower bound and enumerate them
     from the code rather than trusting the number here.
  3. Decide and record what happens when the parent had no --base. Passing an
     explicit main is not the same as passing nothing -- it overrides a repo's
     own frob.toml default. The child must end up with the SAME effective base
     the parent computed, which means forwarding only when the parent's value
     came from somewhere, or forwarding the fully-resolved value including the
     frob.toml contribution. Pick one deliberately and say which.
  4. Audit the other scoping flags at the same time. If --base was dropped by
     all six, check whether --delta and --skip-gates are too; T-0608 already
     records that this family of flags was previously lost at a different layer.

MUST-FIRE FIXTURE:   a ticket whose work sits on a non-main branch, closed with
                     an explicit base naming that branch, produces no diff-driven
                     finding attributable to commits that are on main but not on
                     the ticket's branch.
MUST-STAY-QUIET:     with no base given anywhere, behaviour is byte-identical to
                     today (main), including for a repo with no frob.toml key.
THIRD FIXTURE:       a repo-wide check_base in frob.toml still reaches the nested
                     child, and an explicit flag beats it.

ACCEPTANCE
- Every nested check spawn receives the parent's effective base, enumerated from
  the code rather than from this ticket's list of six.
- The no-base case is explicitly decided and documented, not left implicit.
- The sibling scoping flags audited for the same loss, fixed or ticketed.
- All three fixtures committed.

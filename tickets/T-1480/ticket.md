---
id: T-1480
title: build frob sys check/trace/capacity/threats verbs
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/sys_runner.py
- docs/commands/sys.md
- src/frob/strata/_mutation_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
designated_repro_test: null
threat: null
component: null
---
docs/commands/sys.md documents frob sys as having five verbs today
(plan/doc/export/audit/sync-interface) and names check/trace/capacity/
threats as later phase-5 verbs not yet landed on main. No ticket
currently tracks building these four verbs. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.

## Failure log
- 2026-08-08 attempt 1: Undoable as scoped: adding any of check/trace/capacity/threats as a real,
CLI-dispatchable 'frob sys' verb requires registering a new argparse
subparser in src/frob/_cli_parsers/_misc.py (_add_sys_doc_and_audit_parsers's
sibling registration point, called from both its own top-level 'frob sys'
group at _misc.py:~580 and from _design.py:~57's 'frob design sys'
regrouping mirror) -- both files are explicitly out of scope for this
dispatch (owned by another agent: "Do NOT touch ... src/frob/_cli_parsers/**").

T-1480's declared scope (src/frob/app/sys_runner.py, docs/commands/sys.md,
src/frob/strata/_mutation_audit.py) has no path to a dispatch-reachable
verb without them -- a verb registered only in sys_runner.py's run()
dispatch function with no CLI parser entry can never actually be invoked
(cfg.sys_command would never be set to it by argparse), which is exactly
the "tested components wired into nothing" failure mode this dispatch's
own instructions warn against.

Also found: src/frob/strata/_mutation_audit.py (in this ticket's declared
scope) is unrelated to this ticket's actual work -- it is T-1203/T-1328's
may-capability mutation-audit harness (proves every 'may' declaration is
load-bearing and double-detected), not a sys_runner CLI concern. Same
apparent mis-scoping pattern already found and corrected on T-1482 earlier
in this series (that ticket's declared scope named _mutation_audit.py and
_native_staleness.py, also both unrelated to its actual policy-refinement
work).

Investigated what each of the four verbs would need before concluding
this, per the "check whether the premise is still true" instruction:

- 'check' ("parse + elaborate + prove + report", roadmap.md): this
  premise looks ALREADY SATISFIED by the existing 'frob sys audit'
  (sys_runner.py::_run_audit) -- it parses, elaborates, runs the full
  exhaustiveness/self-conformance/resource-contention/mode-conformance/
  reliability conjunction, and reports pass/fail with named gaps. Adding
  a second, narrower 'check' verb duplicating this would cut against the
  standing "prefer deleting a verb over adding one" directive, not serve
  it -- likely a real one for the CLI-parser-owning agent to drop from
  the roadmap doc rather than build, once that scope opens up.
- 'trace <from> <to>': genuinely new and cheaply buildable --
  'frob.strata._facts.FactBase.reachable(src)' already returns the exact
  witness-path closure this verb would print; only the CLI parser +
  runner glue is missing.
- 'threats [boundary]': 'frob.strata._threat.evaluate_threats' already
  computes the full THREAT001-003 violation set; a boundary-scoped
  filter needs a real join from 'ThreatViolation.node' to the boundary's
  flow endpoints that does not exist anywhere yet -- more design work
  than a CLI wrapper.
- 'capacity [--population N | --at DATE]': no existing evaluator
  projects capacity thresholds against a POPULATION or DATE parameter at
  all ('_starvation.py''s capacity checks are static, not projected) --
  this is new modeling work, not a CLI-glue gap.

Recommendation for whoever next holds src/frob/_cli_parsers/**: 'trace'
is the cheapest real win once the parser files are available; 'check' is
probably better resolved by deleting it from the roadmap doc than by
building a duplicate of 'audit'; 'threats'/'capacity' need real design
work before a CLI verb is meaningful.

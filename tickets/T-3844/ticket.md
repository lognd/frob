---
id: T-3844
title: 'severity ratchet: promote every zero-finding rule to error including VMOD001,
  carve out planning rules as repo-local warnings'
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DIRECTIVE 2026-09-05: "I want all the VMOD errors and EVERY ERROR
POSSIBLE to be an outright error rather than a warning." With one carve-out:
"for this repo because we didn't start out that way, we can suppress the
planning from errors to warnings."

This ticket implements that as a RATCHET, not a flag day, and the measurement
below is what makes it safe to do now.

MEASURED 2026-09-05, `frob check --no-cache` full unscoped run on the live
tree, read through scripts/check_summary.py (never a grep pipeline):

    error    1        <-- the single DOC006, tracked at T-3843
    warning  4765
    info     91
    note     1782

So the ERROR FLOOR IS EFFECTIVELY ZERO. That is precisely the moment to ratchet:
every rule currently sitting at zero findings can be promoted to `error` at NO
COST and can never silently regress again.

WARNING POPULATION BY RULE -- promoting one costs exactly this many findings:

    1270  CPLACE002        26  TEST003          2  REF003
     883  TICK014          21  LANG003          2  PERF005
     879  CPLACE001        19  TICK004          2  EXHAUST002
     474  DOCARCH001       16  god-module       1  god-class
     259  WAIVE004         13  TICK007          1  WALK001
     228  EXHAUST003        8  DOCENUM001       1  TICK012
     156  NARR001           7  (no-code)        1  TICK003
     134  renamed           6  WAIVE010         1  TEST006
      93  EXHAUST004        5  ENV001           1  PERF010
      85  COV006            3  unused-ignore    1  INV005
      75  PERF008           3  possibly-missing-submodule
      50  TEST014           3  NEGEXIST001
      36  DEAD001

    35 distinct warning rules, 4765 findings.

THE WORK, IN THIS ORDER. Do not reorder; step 1 is free and permanent, and it
is most of the owner's intent.

STEP 1 -- PROMOTE EVERY ZERO-FINDING RULE TO `error`. FREE, DO IT FIRST.
Derive the AUTHORITATIVE rule set from the gates registry (`frob.gates._ALL_GATES`
and each gate's own rule ids) -- do NOT use a regex sweep over source strings;
I tried that and got 338 candidate ids that certainly include non-rule strings.
Subtract the 35 rules above. Everything remaining currently emits nothing, so
setting it to `error` in frob.toml's `[gates.severity]` zone reds nothing today
and makes any future occurrence a hard failure. VMOD001 is in this set -- the
owner named VMOD explicitly, and it is free.
Then RE-MEASURE and prove the error count is still 1 (or 0 once T-3843 lands).
If promotion reds the build, some rule was not actually at zero; name it.

STEP 2 -- THE PLANNING CARVE-OUT. The owner's exemption is for rules that
punish this repo for not having been design-first. Enumerate the candidates and
justify each rather than assuming my list: SYS101 (declared-never-observed
capability), DOC006's forward/planned-path references (see T-3829, T-3317,
T-3821), and anything else whose finding means "the design names something that
does not exist yet". Set those to `warn` WITH A COMMENT in the zone naming this
directive and saying the carve-out is repo-local, not a frob default. A
scaffolded design-first repo must still get them as errors -- do not change the
shipped default.

STEP 3 -- FILE THE BURN-DOWNS, DO NOT PROMOTE YET. Each of the 35 rules above
needs its count driven to zero before it can become an error. File one ticket
per rule (or per coherent cluster -- CPLACE001+CPLACE002 are one campaign at
2149 findings, the EXHAUST family is another) recording the CURRENT COUNT as the
denominator. Do not promote any of them in this ticket. A rule promoted while it
still fires reds the build for everyone and teaches people to ignore the gate.

WHAT NOT TO DO:
- Do not promote a rule with findings "because most are waived" -- the counts
  above are unwaived findings as reported.
- Do not raise severity by editing rule definitions in code. The severity
  mechanism is frob.toml's `[gates.severity]` T-1002 managed zone; use it, and
  keep the zone markers intact.
- Do not touch `[testing]` floors or the ratchet locks; unrelated.
- Do not silence anything to make step 1's re-measurement clean.

ACCEPTANCE
- The authoritative zero-finding rule set derived from the registry, listed in
  the done report, and promoted to `error`.
- Post-promotion full `--no-cache` re-measurement showing the error count
  unchanged (1, or 0 after T-3843).
- The planning carve-out enumerated and justified per rule, repo-local only.
- One burn-down ticket per remaining warning rule/cluster, each carrying its
  measured denominator.

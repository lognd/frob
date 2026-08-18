---
id: T-2495
title: declare may exec for gates node covering _mutation_evidence.py's direct guarded_subprocess_run
  call
state: done
kind: security
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- src/frob/gates/_mutation_evidence.py
evidence_scope:
- tests/test_gates_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: remove the 3 interim SELFAUDIT001 waivers now that the may exec declaration
    this ticket was filed for already exists (landed incidentally by T-2409)
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_confirmatory_finding_is_warn_for_feature_kind
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 89d13c31bda338182cc06b0c2b9d71bf220c1278
---
T-2480 changed src/frob/gates/_mutation_evidence.py::_spawn_designated_test
to call frob.process._guard.guarded_subprocess_run DIRECTLY (catching
subprocess.TimeoutExpired itself, to distinguish a genuine TIMEOUT
outcome from run_argv's own generic Err(GitError.GitFailed) collapse)
rather than going through frob.gitio.run_argv the way every other
subprocess call in this file already does. SELFAUDIT001 (SYS100) flagged
this as a new, undeclared direct "exec" capability observation in the
gates node's design/frob.strata declaration.

design/frob.strata's "gates" node (line ~349) is currently held by
T-2487's live scope lease, so T-2480 could not add "may \"exec\";" to it
directly and instead waived SELFAUDIT001 at the three flagged call sites
with a reasoned justification: the underlying exec capability was
already effectively granted transitively (this same module already
spawns subprocesses via frob.gitio.run_argv, which itself declares
"may \"exec\"") -- this change only moves WHICH function in the call
chain issues the syscall, for the specific and narrow purpose of
catching subprocess.TimeoutExpired before run_argv's own internal
try/except would collapse it into an indistinguishable generic error.

Once T-2487's lease on design/frob.strata clears: add "may \"exec\";" to
the gates node's declaration (or a via-scoped variant naming
src/frob/gates/_mutation_evidence.py specifically, matching this file's
own precedent elsewhere in the strata file), then remove the three
frob:waive SELFAUDIT001 directives T-2480 added.
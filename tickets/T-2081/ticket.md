---
id: T-2081
title: COV001/DOC002/SELFAUDIT001 fire on src/frob/strata/_claims.py, surfaced by
  T-2076's land-parity fix
state: dropped
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_claims.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while working T-2076 (land-time gate spawn under FROB_AGENT):
once T-2076's fix let the land-time gate spawn actually run (instead of
silently refusing under FROB_AGENT and reading as "unmeasured"), `frob
check --land-parity` on this checkout surfaces 3 pre-existing unscoped
errors, all in a file T-2076 never touches (`src/frob/strata/_claims.py`,
last changed by T-1763, 2026-08-07, unrelated to T-2076):

  COV001 src/frob/strata/_claims.py -- evaluate_claims is public with no
  frob:doc edge (the file DOES carry a `# frob:doc
  docs/strata/kernel.md#claim-evaluation` line directly above the
  function -- the gate is not recognizing it; needs investigation into
  why).
  DOC002 src/frob/strata/_claims.py
  SELFAUDIT001 design

Confirmed pre-existing and out of T-2076's scope: `git diff --stat main --
src/frob/strata/_claims.py` is empty on T-2076's branch. These findings
were themselves silently escaping every land's re-verification for the
same T-2076 reason (the FROB_AGENT refusal made check_gates() vacuously
"unmeasured") until T-2076's fix; now that the spawn runs for real, they
are visible and need a real fix or waiver.

## Drop reason
- 2026-08-10: COV001/DOC002 on src/frob/strata/_claims.py resolved by T-1669's own land (docs/strata/kernel.md's Claim evaluation section); SELFAUDIT001 no longer fires either (re-measured on the merged tree, land-parity clean) -- neither finding reproduces any more

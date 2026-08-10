---
id: T-1998
title: 'post-land sweep regression from T-1977: 5 new (rule, file) identit(ies), 8
  finding(s) (AFFECT001, COV002, REL002, TEST001)'
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .frob-release.json
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/app/ticket_runner/_new.py
evidence_scope:
- tests/unit/test_ticket_new_related.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match
- tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_no_match_for_a_genuinely_distinct_title
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1977 at commit f3257572abbd7bf215b9cd66a9c6948c8c223df3 found 5 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (5), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 8 actual finding(s) across those 5 identit(ies).

New (rule, file) identit(ies) filed here:

- AFFECT001  src/frob/_cli_parsers/_ticket/_new.py
- AFFECT001  src/frob/app/ticket_runner/_new.py
- COV002  src/frob/app/ticket_runner/_new.py
- REL002  .frob-release.json
- TEST001  src/frob/app/ticket_runner/_new.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- AFFECT001  src/frob/_cli_parsers/_ticket/_new.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- AFFECT001  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REL002  .frob-release.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST001  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
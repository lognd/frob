---
id: T-2010
title: Populate frob.toml min_frob_version in this repo and the 8 sibling repos so
  T-1218's stale-binary warning actually fires
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: populate min_frob_version key in this repo's frob.toml only, per coordinator
    scoping
  actor: logan
  at: '2026-08-10'
evidence:
- cmd:grep -n "min_frob_version" frob.toml exit=0 sha256=fffd1fe2e0ed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
## Done report

Changed: frob.toml (added top-level `min_frob_version = "0.447.0"`)

T-1218's `frob.app._config_meta.stale_binary_warning` mechanism has been
live since it landed but never fired anywhere because no repo -- this one
included -- had ever set the `min_frob_version` key it reads. Populated
it in this repo's own `frob.toml`, scoped to THIS repo only per the
coordinator's explicit note (the 8 sibling repos are a separate rollout
needing a human decision).

Verified the warning actually fires, not just that the key parses:
`stale_binary_warning(Path('.'), running_version='0.100.0')` returns the
full warning string naming the declared floor; `running_version=None`
(the real installed version, 0.447.0) returns `None` (no false-positive
nag on a current checkout). Also independently confirmed via this
session's own tooling: the `frob-version-skew` pre-tool-call hook fired
on a bare `frob --version` invocation, reporting the on-PATH global
install at 0.184.0 against this checkout's 0.447.0 -- the exact stale-
binary scenario T-1218/T-2010 exist to surface.

Evidence: cmd:grep -n "min_frob_version" frob.toml (docs-kind ticket,
non-pytest evidence channel).

Gates: `frob check --ticket T-2010` -- 0 errors in every ticket-scoped
gate family. The one repo-wide FAIL present (gate:COV, tickets/T-0907's
own stale evidence citation) is the same pre-existing, unrelated finding
already disclosed in T-1925/T-1927/T-2004's reports this series --
confirmed unrelated by the finding's own self-identification (it names
a different ticket's ledger entry, not any file this ticket touched).

### Changed
```
 tickets/T-2010/ticket.md | 13 ++++++++++++-
 1 file changed, 12 insertions(+), 1 deletion(-)
```

### Evidence
- `cmd:grep -n "min_frob_version" frob.toml exit=0 sha256=fffd1fe2e0ed` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/unit/test_tickets_evidence_only_scope.py

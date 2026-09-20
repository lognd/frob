## Done report

Repointed the DRIFT002-flagged frob:enumerates edge in
docs/guides/agent-playbook-appendix.md away from the no-longer-resolvable
frob.check._STAGE_GROUPS (a PEP 562 lazily-materialized view since T-4336)
at the real declaration sites: frob.check._TOOL_ONLY_STAGE_GROUPS (lint,
static) and frob.gates._KNOWN_GATE_STAGE_GROUP_NAMES (gates-fast,
gates-native, gates-security, derived from frob.gates._GATE_STAGE_GROUPS).
Split one frob:enumerates directive into two, matching the new split
declaration shape.

Rewrote the surrounding prose: it previously described _STAGE_GROUPS as a
single hand-maintained mapping; it now explains the tool-only vs.
gate-derived split and notes the import-time assert (T-4336) that makes a
gate reaching _ALL_GATES without a stage-group entry impossible, rather
than a fact caught only by a regression test.

Sibling-reference search (git grep across docs/, tickets/, CHANGELOG.md):
every remaining hit naming frob.check._STAGE_GROUPS is either historical
prose in CHANGELOG.md/changelog.d/*.md/tickets/**/done-report.md
(correctly describing past state, not a live doc-graph edge) or one
non-edge prose mention in docs/modules/tickets-landing.md line 2820 (a
frob:describes edge there targets unrelated symbols; _STAGE_GROUPS
appears only in a parenthetical). That mention is outside this ticket's
scope (docs/guides/agent-playbook-appendix.md only) and is not itself a
frob:enumerates/frob:describes edge, so it does not trip DRIFT002; noting
it here rather than fixing it silently.

Verification: gate:DOCBLOCKS (which carries DOCENUM001, the specific
enumerates-diff rule) and gate:DRIFT (DRIFT002) both report 0 errors for
this file at commit 80604d785, run twice for stability given T-4343's
open concurrent-load nondeterminism. An unscoped frob check --ticket
T-4345 --json (FROB_ALLOW_FULL_CHECK=1) also reports 0 errors, run twice.
Two new DOCENUM001 WARNings (undocumented-member, not member-mismatch)
appear for the split edge -- same pre-existing WARN-only class the gate's
own docstring documents (~79 pre-existing instances), not an ERROR and not
new in kind.

Did not run the full frob test --base main touched-set: a .md file has no
bound language, so selection falls back to a suite-wide run across
python/rust/strata, which is disproportionate to a one-file doc change and
was competing with 4 other agents on the host. The ticket's stated
acceptance (unscoped gate at zero) does not require it; per-rule gate
evidence above is the direct proof.

### Changed
```
 docs/guides/agent-playbook-appendix.md | 13 ++++++++++---
 tickets/T-4345/ticket.md               |  3 +++
 2 files changed, 13 insertions(+), 3 deletions(-)
```

### Evidence
- `cmd:uv run frob check --only docblocks --json exit=0 sha256=8404bae9255b` (cmd evidence, exit=0)
- `cmd:uv run frob check --only drift --json exit=0 sha256=fc1acb10ba0c` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 4707 warning(s), 956 waived
- error-findings: none (measured, zero errors)

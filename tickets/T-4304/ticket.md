---
id: T-4304
title: nothing ever sweeps the whole tree for formatting drift, so a file nobody touches
  can stay unformatted indefinitely
state: dropped
kind: bug
origin: human
created: '2026-09-08'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a file that no land has touched since it drifted, when the periodic
    check runs, then the drift is detected without waiting for an integration run
    to fail
  evidence: []
- text: given the periodic check finds drift, when it acts, then what it does with
    the finding is a recorded decision rather than an unread report
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE LAND-TIME FORMATTING GATE IS DIFF-SCOPED BY DESIGN, WHICH IS CORRECT, AND IT LEAVES ONE GAP NOTHING ELSE COVERS.

The gate added today checks only the files a land actually touches. That is the right default: it keeps land latency proportional to the change, and it makes the finding attributable to whoever introduced it, while the drift is still cheap to fix. Nothing here argues for widening it to scan the whole tree on every land.

THE GAP. A file that no land happens to touch can sit unformatted indefinitely, because the only thing that would notice is a whole-tree check, and the only whole-tree check runs in the integration workflow -- where it surfaces as a red run attributed to nobody, long after the fact. That is precisely how the drift cleared today accumulated: two files went unformatted for hours, were invisible to the new gate because no land touched them again, and were found only because someone read a failing run's tool summary.

WHAT THIS SHOULD BE. A periodic whole-tree check, scheduled rather than on the land path. The recommendation came from the agent that cleared the residual drift, and its reasoning is sound: this closes the detection gap without making every land pay for a full scan.

DECIDE WHAT IT DOES WHEN IT FINDS SOMETHING. A scheduled job that merely reports has a way of becoming noise nobody reads. Consider whether it should open a ticket, or simply apply the formatter and land the result itself, given that the operation is deterministic and reviewable. Record the choice.

THIS IS DELIBERATELY LOW PRIORITY. The land-time gate stops NEW drift, which was the bleeding. This only covers the residue, and the residue is currently zero -- the tree is fully formatted as of today. File it so the gap is written down rather than rediscovered.

## Drop reason
- 2026-09-09: 2026-09-09: T-4323 (landed 39eb2a10d) added the auto-APPLY half of LANDFMT001, so a land now REWRITES drift in the .py files it touches instead of only refusing. Measured current state: 'ruff format --check .' reports 1479 files already formatted, zero drift repo-wide (matches the ticket's own note). Re-examined what could still produce drift now that touched-file repair is automatic:
- Drift from ORDINARY edits: closed. Any land touching a .py file now self-heals via _ruff_format_pre_land_step (T-4323); a file untouched by any land cannot silently accumulate the kind of drift this ticket described, because that kind (edited-but-not-reformatted) no longer survives a land.
- The one path left: a formatter VERSION or RULE-SET bump (a pyproject.toml pin change) can reformat the whole tree at once without any of those files appearing in a land's own diff, so LANDFMT001's diff-scoped repair does not see it. This is the actual residual scope -- much narrower than "a scheduled whole-tree sweep."
- That residual event is rare, deliberate, and already reviewable at the point it happens: whoever bumps the pin can and should run 'ruff format .' in the same change. Sizing a perpetual scheduled job (with its own land/report/apply machinery) to cover an event that occurs only when someone edits one pinned version string is disproportionate to the exposure, and this drive's own precedent (T-4323/T-1900) favors deterministic auto-apply over standing report infrastructure -- but there is no live drift to apply against today, so there is nothing to build against.
Practically also blocked: T-4304's only declared scope is .github/workflows/ci.yml, which collides with in-progress T-4360's lease on .github/workflows/*.yml ('frob ticket start T-4304' refused with this collision), and this session's brief separately bars touching the CI workflow, pyproject.toml, and frob.toml. Combined with the judgement above -- the residual gap is a version-bump-time discipline, not a standing sweep -- dropping is the correct outcome rather than forcing scope into files under active lease/embargo. If a future formatter bump ever needs a mechanical guard, it belongs on the pyproject.toml-diff path (assert the touched-set-plus-whole-tree check on any ruff-pin change), not a cron sweep, and should be a fresh ticket sized to that.

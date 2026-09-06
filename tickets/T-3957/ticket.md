---
id: T-3957
title: 'SCOPE002 doc-closure on docs/guides/release.md is unclosable: any ticket touching
  scripts/artifact_smoke.py inherits an unbounded doc-anchor cascade'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/release.md
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
found while working T-3935. scripts/artifact_smoke.py (from T-3884) carries pre-existing frob:doc anchors into docs/guides/release.md#artifact-smoke-stage-t-3884. Any ticket that declares scripts/artifact_smoke.py in its scope (as T-3884s own scope did, and T-3935s does) must therefore also put docs/guides/release.md in FULL scope to satisfy SCOPE002 -- confirmed reproducible even with a completely unmodified artifact_smoke.py, purely from the ticket scope declaration.

MEASURED: adding docs/guides/release.md to scope then cascades SCOPE002 further, because that SAME doc also anchors scripts/verify_release_ci_status.py (#verify-ci-status, added later, presumably by T-3251) and src/frob/doctor.py (#native-acceleration-degrade-doctrine-t-3011, added later). Neither of those tickets scope-declared docs/guides/release.md fully at the time, so the debt was never surfaced until a LATER, unrelated ticket (T-3935) tries to declare the whole file in scope. --demote-to-evidence-only does not satisfy SCOPE002 (verified: the gate only accepts full write scope). Full-scoping doctor.py cascades a SECOND level into docs/guides/install.md and docs/modules/cli.md (91+ more warnings) via OTHER, unrelated doctor.py symbols -- unbounded in practice.

This matches the exact tension already documented and waived in src/frob/gates/_rule_id_scan.py (T-1010/T-1937 frob:waive COV001 comments): a frob:doc anchor into a monolithic shared doc can make SCOPE002 closure disproportionate to a tickets actual diff. T-3935 worked around this for its OWN new code with the same frob:waive COV001 pattern (skip the frob:doc directive on new symbols entirely), but cannot retroactively edit T-3884-owned pre-existing directives (SmokeCheckError, check_base_install, check_serve_extra, check_native_extra, main) without scope creep.

Proposed fix (for whoever picks this up): either (a) split docs/guides/release.md#verify-ci-status and #native-acceleration-degrade-doctrine-t-3011 into their own smaller docs so the artifact-smoke-stage section closure does not pull them in, or (b) change SCOPE002s closure semantics so citing an EXISTING, already-satisfied anchor (one whose describing symbols are already fully documented, per a prior tickets close) does not re-demand the whole docs other unrelated anchors just because a later ticket also cites the same file. Left un-fixed, T-3935 close cites this ticket and leaves its own scope as the original 5 files (no docs/guides/release.md), accepting the resulting SCOPE002 as pre-existing.
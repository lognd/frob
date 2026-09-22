---
id: T-5139
title: 'Missing or failing external tools are loud: one tool registry, Result-typed
  adapters, an UNMEASURED summary block at the end of every check and land, non-zero
  exit when a relevant tool is absent'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: critical
parent: null
tier: story
sprint: v0.533.0
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor.py
- src/frob/vet/_osv.py
- src/frob/vet/_scan.py
- docs/modules/check.md
- docs/modules/vet.md
- docs/guides/install.md
scope_breadth_ack: true
scope_breadth_ack_reason: one registry consumed by every adapter plus the check and
  land summary that renders it
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/check/*.py
  reason: 'T-5139 collided with two live leases at start time: src/frob/gates/__init__.py
    held by T-5135, src/frob/check/__init__.py held by T-4692 (in-progress). Narrowing
    to the tool registry + Result-typed adapters + doctor integration (src/frob/doctor.py,
    src/frob/vet/_osv.py, src/frob/vet/_scan.py, docs) this ticket CAN land now; the
    frob check/frob ticket land UNMEASURED summary wiring is filed as a follow-up
    once T-4692/T-5135 close'
  actor: logan
  at: '2026-09-21'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: 'T-5139 collided with two live leases at start time: src/frob/gates/__init__.py
    held by T-5135, src/frob/check/__init__.py held by T-4692 (in-progress). Narrowing
    to the tool registry + Result-typed adapters + doctor integration (src/frob/doctor.py,
    src/frob/vet/_osv.py, src/frob/vet/_scan.py, docs) this ticket CAN land now; the
    frob check/frob ticket land UNMEASURED summary wiring is filed as a follow-up
    once T-4692/T-5135 close'
  actor: logan
  at: '2026-09-21'
- op: add
  glob: docs/guides/install.md
  reason: doctor.py's existing frob:doc public-api anchors point at docs/guides/install.md;
    new tool-registry symbols there need the same doc home
  actor: logan
  at: '2026-09-21'
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: given Cargo.lock in the repo and cargo-audit absent, when frob check runs,
    then the run ends with an UNMEASURED block naming cargo-audit, VET005 and the
    install command, and exits non-zero
  evidence: []
- text: given osv reachable but returning unparseable JSON, when frob vet runs, then
    VET005 is reported UNMEASURED with the stderr tail, never clean
  evidence: []
- text: given no Cargo.lock, when frob check runs, then cargo-audit is listed as not
    needed and does not affect exit
  evidence: []
- text: given --allow-missing-tool sqlfluff --reason X, when frob ticket land runs,
    then the land proceeds and the reason is recorded on the ticket
  evidence: []
- text: given a new shutil.which call outside frob.tools, when frob check runs, then
    a DUP or ARCH finding names the registry
  evidence: []
threat: null
component: check
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: when a tool is missing (cargo-audit, osv-scanner, sqlfluff, squawk, gh, a build system) or any step of an adapter fails, the run must be LOUD at the end, never a quiet skip. MEASURED today: doctor already owns an _EXTERNAL_TOOLS inventory with REQUIRED/optional categories (T-3276) but check and land do not consume it; 18 separate shutil.which call sites decide presence locally; an absent osv-scanner is an INFO log plus a 'skipped' note and the rule counts as clean (this is how VET005 never ran here without anyone noticing); vet.required_tools exists but is opt-in per tool. DESIGN: (1) One registry: promote doctor's inventory to frob.tools.REGISTRY, each entry {name, kind binary|package, purpose, rules_it_serves, relevant_when (a repo predicate: Cargo.lock present, *.sql present, package.json present, .github/workflows present, tests present...), install_remedy per platform, version_min}. Every adapter looks up presence through it; the 18 ad-hoc which() sites are replaced (DUP rule fires on a new bare shutil.which in src/frob outside the registry). (2) Result-typed adapters: every spawn returns typani Result[ToolOutput, ToolFailure] where ToolFailure is an enum: Missing, VersionTooOld, SpawnFailed, NonZeroExit, Timeout, UnparseableOutput, NetworkUnavailable. UnparseableOutput and Timeout are NOT clean (wrapper exit code is not the work; silent zero). (3) Relevance decides severity: a tool whose relevant_when predicate is true for this repo and is Missing or failed makes every rule it serves UNMEASURED and the run exit non-zero (new rule TOOL001 missing-relevant-tool, TOOL002 tool-failed, TOOL003 tool-too-old); an irrelevant tool is listed once as 'not needed here'. Override is one flag per tool with a reason, --allow-missing-tool NAME --reason, recorded like a waiver. (4) Loud summary: every frob check, frob vet, frob test and frob ticket land ends with an UNMEASURED block, printed last and coloured, listing rule family -> tool -> failure kind -> remedy command; the --json output carries the same list under unmeasured[]; land refuses when the block is non-empty for a relevant tool (same override flag). (5) Bootstrap: frob doctor --install prints or runs the remedy commands for every missing relevant tool (uv tool install sqlfluff squawk-cli pip-audit; cargo install cargo-audit; gh via package manager); CI runs doctor first and fails on TOOL001. (6) Every step: adapters log spawn argv, exit, duration and bytes at DEBUG; a partial pipeline (tool ran, parse failed) reports the raw tail of stderr in the block. (7) Docs: check.md and vet.md gain the UNMEASURED contract and the registry table is generated from the registry (DOC drift-lock).
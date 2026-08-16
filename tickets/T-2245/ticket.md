---
id: T-2245
title: Rewrite docs + agent-playbook to name frob subcommands first; audit remaining
  Makefile references in src/frob/**
state: queued
kind: docs
origin: human
created: '2026-08-16'
priority: medium
blocked_by:
- T-2240
- T-2241
- T-2242
- T-2244
parent: T-1382
tier: ticket
sprint: null
runs_last: false
scope:
- docs/guides/agent-playbook.md
- docs/index.md
- docs/rework.md
- docs/commands/sync-skills.md
- docs/commands/release.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: narrow epic-breadth docs/** to the specific pages this leaf actually rewrites
    (playbook + top-level index/rework pages + the two new command doc pages T-2241/T-2242
    create); a repo-wide docs/** lease would block every other in-flight docs-touching
    ticket for no reason since the audit half of this leaf is read-only measurement,
    not a doc edit
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: narrow epic-breadth docs/** to the specific pages this leaf actually rewrites
    (playbook + top-level index/rework pages + the two new command doc pages T-2241/T-2242
    create); a repo-wide docs/** lease would block every other in-flight docs-touching
    ticket for no reason since the audit half of this leaf is read-only measurement,
    not a doc edit
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/index.md
  reason: narrow epic-breadth docs/** to the specific pages this leaf actually rewrites
    (playbook + top-level index/rework pages + the two new command doc pages T-2241/T-2242
    create); a repo-wide docs/** lease would block every other in-flight docs-touching
    ticket for no reason since the audit half of this leaf is read-only measurement,
    not a doc edit
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/rework.md
  reason: narrow epic-breadth docs/** to the specific pages this leaf actually rewrites
    (playbook + top-level index/rework pages + the two new command doc pages T-2241/T-2242
    create); a repo-wide docs/** lease would block every other in-flight docs-touching
    ticket for no reason since the audit half of this leaf is read-only measurement,
    not a doc edit
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/commands/sync-skills.md
  reason: narrow epic-breadth docs/** to the specific pages this leaf actually rewrites
    (playbook + top-level index/rework pages + the two new command doc pages T-2241/T-2242
    create); a repo-wide docs/** lease would block every other in-flight docs-touching
    ticket for no reason since the audit half of this leaf is read-only measurement,
    not a doc edit
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/commands/release.md
  reason: narrow epic-breadth docs/** to the specific pages this leaf actually rewrites
    (playbook + top-level index/rework pages + the two new command doc pages T-2241/T-2242
    create); a repo-wide docs/** lease would block every other in-flight docs-touching
    ticket for no reason since the audit half of this leaf is read-only measurement,
    not a doc edit
  actor: logan
  at: '2026-08-16'
designated_repro_test: null
acceptance:
- text: GIVEN docs/ and docs/guides/agent-playbook.md WHEN a migrated workflow (coverage,
    sync-skills, release publish, format/lint/typecheck/test) is described THEN it
    names the frob subcommand first, with 'make <target>' documented only as an optional
    thin alias
  evidence: []
- text: GIVEN every 'Makefile' reference still present in src/frob/** after T-2240/T-2241/T-2242/T-2244
    land THEN each is classified as either (a) a scaffold template constant generating
    a Makefile for a SCAFFOLDED downstream project (out of scope for this repo's own
    workflow), (b) gate/doc-link code that legitimately treats the Makefile as a citation
    target (DOC010 etc, also out of scope), or (c) a genuine leftover this epic should
    have closed but did not -- and any (c) finding gets its own follow-up ticket,
    not silently dropped
  evidence: []
- text: GIVEN T-1382's three acceptance criteria (no-Makefile workflow parity; Windows-shape
    coverage workflow; docs naming frob first) THEN this leaf's Done report states,
    with evidence, whether each is now met, partially met, or still open, and closes
    or narrows T-1382 accordingly
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
Final leaf of the T-1382 series. Blocked on T-2240 (coverage), T-2241 (sync-skills), T-2242 (release publish), T-2244 (trivial alias repoint) because it documents the LANDED state of all four, not an aspirational one, and because it edits the same docs/agent-playbook territory those leaves' own Done reports will already touch for their specific workflow. Also performs the ticket body's original decomposition item 3 (audit the 21 src/frob/** Makefile references) as a MEASUREMENT step at leaf-start time, not from the original 2026-08-01 count, since that count is stale (measured today: still git-grep-locatable across src/frob/_cli_parsers/_core.py, gates/__init__.py, gates/_doclink_docanchor.py, gates/_root_asset_dirs.py, gates/_waive.py, natives/_build.py, scaffold/__init__.py, scaffold/_managed.py, scaffold/_pool.py, scaffold/project.py, strata/_native_staleness.py, testing/_collect_cpp.py, testing/_coverage_cache.py, testing/_coverage_refresh.py, testing/_coverage_wait.py, vet/_capability_registry/_matrix.py, vet/_supplychain.py -- more files than the original body's list of 8, and a first read suggests most are ALREADY either scaffold-template constants or gate/doc-citation code that legitimately mentions Makefile, not undone workflow-coupling; this leaf's job is to confirm that with evidence per file, not re-decompose them into new work by assumption).
---
id: T-2135
title: 'DOC006 remaining 88: repair live docs/** CLI/anchor/symbol pointers, triage
  49 live (non-archived) ticket-body findings'
state: queued
kind: docs
origin: human
created: '2026-08-11'
priority: high
parent: T-0969
tier: ticket
sprint: null
runs_last: false
scope:
- docs/commands/refactor.md
- docs/design/cli-regrouping.md
- docs/guides/agent-playbook.md
- docs/guides/agentic-time-profiling.md
- docs/guides/claude-hooks.md
- docs/modules/gates.md
- docs/modules/stats.md
- docs/modules/strata.md
- docs/strata/reliability.md
- docs/strata/roadmap.md
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: docs/** was too broad (2956 scope-closure warnings); narrowing to the exact
    12 files DOC006 actually flags
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/commands/refactor.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/guides/agentic-time-profiling.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/modules/gates.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/modules/stats.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/modules/strata.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/strata/reliability.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/strata/roadmap.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/strata/surface.md
  reason: 11 of the 12 live doc files DOC006 flags after T-2131's archive exclusion;
    docs/modules/tickets.md excluded here -- it is currently leased/in-progress on
    3+ other tickets (T-1973 et al), add once free
  actor: logan
  at: '2026-08-11'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-0969/T-2131 residue. After T-2131's archive-directory exclusion, DOC006
dropped from 584 to 88 (measured 2026-08-11). The remaining 88 need real
per-pointer judgment, not a categorical exclusion, split two ways:

25 findings across ~13 files under `docs/**` (genuinely live docs,
broken CLI/anchor/symbol pointers) -- includes at least: several `frob
sys sync-interface`/`frob worktree release-lease`/`frob graph
select-batch-tests` invocations that no longer resolve (renamed or
removed subcommands), a couple of `--agentic`/`--force` flags that no
longer exist on their named subcommand, a few dead doc-anchor links
(`#11b`, `#tick003`, `#drift-lock-stale-waivers-fail`), and 2-3 code-
symbol pointers (`frob.strata._sync_interface`,
`frob.gates._inv006_split_assist`) that may have moved or been renamed
rather than removed. `docs/modules/tickets.md` alone carries 8 of these
-- NOTE it is a contended file (see T-1899/T-1952/T-1996/T-1973/T-1860,
all queued against it); coordinate scope before starting.

~49 findings across 32 files under live (not yet archived) `tickets/T-*/
{ticket,done-report}.md`. Unlike the archived case, these tickets are
still open or only recently closed -- some may be genuinely stale
pointers worth a real fix (if the ticket body is still being read as
live guidance), others may be legitimate historical narrative in a
ticket that simply has not been archived yet (same argument as the
500 already excluded, just not old enough to have moved to `tickets/
archive/**`). This needs per-file judgment, not a blanket third
exclusion category -- and touching other tickets' own bodies is its own
scope question this ticket should not decide unilaterally.

Full per-file/per-line list is reproducible via:
    frob check --only docblocks --json | <filter DOC006, exclude
    tickets/archive/** and tickets.md>

Do NOT add 88 individual waivers as a shortcut -- fix the genuinely
broken live pointers.

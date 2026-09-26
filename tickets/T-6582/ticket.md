---
id: T-6582
title: land self-conformance DOC006 builds the base CLI tree from the pre-merge process,
  so a verb added by the landing ticket is reported as unresolved
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/gates/_docblocks_refs.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names external or future-facing paths (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-26'
  old_length: 1096
  new_length: 1308
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-26 landing T-5784 (adds `frob coord status`): the land's
self-conformance pass (T-3324) refused with "DOC006: cli invocation pointer
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->in docs/modules/coord.md:1 does not resolve -- `frob coord status` does not
resolve to a known subcommand", while `_subparser_tree(_build_parser())`
inside the worktree resolves coord -> status fine. The pre-merge DOC005
guard already loads the parser factory from the merge-candidate root
(T-2941, `_load_parser_factory_from_root`), but the self-conformance DOC006
run uses `_console_trees`' default in-process loader, i.e. the running
land process's pre-merge `frob` package, which has no coord verb yet.
Workaround used: inline DOC006 waivers on the two pointer lines.

Deliver: the self-conformance pass threads the same root-bound loader as
the DOC005 guard so a verb registered by the landing ticket resolves;
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->remove the T-5784 workaround waivers in docs/modules/coord.md. Positive
control: a fixture where a doc points at a verb that exists only in the
candidate tree; the in-process loader reports DOC006, the root-bound
loader does not.

---
id: T-2559
title: DOC006 flag resolution has the same _build_parser()-mirror-drift false positive
  T-2533 fixed for subcommand chains
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_docptr.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: avoid backtick-wrapped bogus/gap CLI invocations tripping DOC006 on the
    ticket's own body (land-blocking as of T-2374)
  actor: logan
  at: '2026-08-18'
  old_length: 1686
  new_length: 1665
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2533 (DOC006 CLI-invocation subcommand-chain false
positive fix). T-2533's fix patches _docblocks_refs.py's _console_trees
subcommand-CHAIN resolution for _dispatch_*-bypassed verbs (worktree,
release publish) -- it does NOT touch _docptr.py's separate FLAG
resolution path (_leaf_parser/console_parsers), which still walks
_build_parser()'s own decorative --help-only mirror parser objects
directly, not the real dispatch-time parsers.

Confirmed live: worktree sweep has a genuinely real --force flag
(src/frob/app/worktree_runner.py::_build_worktree_parser registers it,
T-1739) but src/frob/_cli_parsers/_core.py::_add_worktree_parser's
--help-only mirror of worktree sweep never registered it (only
registered path/--dry-run/--min-age). DOC006 flags a doc citing that
flag as "not a known option", a false positive in the same root-cause
class T-2533 fixed for subcommand chains, but at the flag level instead.

Left a frob:waive DOC006 at the one live doc site
(docs/modules/tickets-landing.md, the "worktree sweep --force" mention)
rather than silently letting this remain unresolved without disclosure.

Fix, mirroring T-2533's own approach: give DOC006's flag-resolution path
(src/frob/gates/_docptr.py::_cli_violations/_leaf_parser/
_console_parsers) the same bypass-subtree-patch treatment T-2533 gave
the subcommand-chain tree in _docblocks_refs.py -- either patch the
PARSER OBJECT (not just the tree dict) for bypassed verbs before flag
lookup, or extend _leaf_parser to consult the real dispatch-time parser
factory directly when the chain crosses a known bypass boundary. After
the fix, remove the one waiver this ticket adds.

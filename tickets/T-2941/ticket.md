---
id: T-2941
title: 'frob ticket land: DOC005 pre-merge guard checks a same-diff new subcommand
  against a stale, pre-merge registry (refuses forever, unwaivable)'
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/gates/_docblocks_refs.py
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
`frob ticket land`'s pre-merge "does-not-worsen" guard for DOC005
(`frob.app.ticket_runner._land_cmd._doc005_checker`, T-2285) resolves the
"live" subcommand registry via `frob.gates._docblocks_refs._load_parser_
factory` -> `resolve_dotted_symbol("frob.__main__:_build_parser")`, which
is a plain `importlib` resolution against whatever `frob` package is
ALREADY installed/importable in the CURRENT process -- it does not sandbox
the import against the `worktree`/merge-candidate content at all (the
`worktree` argument is used only to locate `frob.toml`'s
`[[docblocks.commands]]` declaration, never to scope the actual Python
import).

Reproduced directly this session (T-2911): a ticket that adds a new
top-level subcommand (`frob status`) AND updates its own `README.md`
command-table row/count in the same diff gets refused at land time, every
single retry, with:

    DOC005: README.md table row `frob status` names a subcommand that no
    longer exists in the live `frob.__main__:_build_parser` registry
    DOC005: README.md claims 47 commands but the live registry has 46

...even though the worktree's own standalone `frob check --only docblocks`
(run directly against the worktree, no land involved) reports the SAME
README content as fully correct (47/frob status resolves) once natives are
built and the module is imported fresh in a worktree-rooted process. The
land-time guard's "live registry" is necessarily ONE COMMIT STALE inside
the same land that would introduce the new subcommand, because the check
runs before (or without properly re-importing after) the merge actually
writes the new `src/frob/__main__.py` content to the checkout the running
land process's own `sys.path` resolves against -- confirmed by reading
`_doc005_checker`/`_console_trees`/`_load_parser_factory`'s source: none of
them re-point the import at the merge-candidate tree.

This is NOT relaxed by the rapid profile (the refusal message says so
explicitly) and NOT waivable -- `frob:waive DOC005` is silently rejected
by the markdown-directive allowlist (`gate:DSL` DSL001: "only ['BUG002',
'DOC004', 'DOC006', 'INV003', 'INV004', 'REF001', 'REF002'] are read from
markdown waivers"), even though the land refusal message itself suggests
`frob:waive DOC005` as an escape hatch -- a second, smaller bug (the
refusal's own suggested remedy does not work for this rule).

Impact: any ticket that adds or removes a top-level subcommand and updates
its own README.md table/count in the same diff cannot land, ever, without
either (a) splitting the change across two lands (land the code first,
land the doc update second, once the registry is "live" from a PRIOR
land) or (b) reverting the README edit and filing a doc-catchup follow-up
(what T-2911 did to unblock itself).

Suggested fix direction (not implemented here, out of T-2911's declared
scope -- `_land_cmd.py`/`_docblocks_refs.py` are core land/gate machinery):
`_load_parser_factory`/`_console_trees` need to build the "live" tree from
the actual post-merge candidate tree (e.g. via `importlib.util.spec_from_
file_location` pointed at the candidate's own `frob/__main__.py`, or by
re-running this specific check as a genuinely fresh subprocess with a
`PYTHONPATH`/`sys.path` rooted at the merge candidate) rather than the
running land process's own already-imported package. Separately,
`_land_cmd.py`'s refusal message should stop suggesting `frob:waive
DOC005` if DOC005 waivers are structurally never honored from markdown.

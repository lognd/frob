## Done report

Root cause: `frob ticket scope`'s `--reason`/`--reason-file` are plain
single-value argparse options (default `store` action). Passing either
flag twice on one command line silently keeps only the LAST value,
matching the T-3403 measurement exactly (two --reason flags, intended to
pair with two --adds, collapsed into one shared reason applied to both
scope_changes entries -- the first glob's real reason was discarded with
no warning).

DESIGN DECISION (as requested, stated explicitly, not just implemented):
the chosen semantic is that ONE `--reason` applies to EVERY --add/
--remove/--demote-to-evidence-only glob a single `frob ticket scope`
invocation mutates -- this was already the intended design per the
pre-existing docstring on `_add_ticket_scope_parser`, just unenforced
and unsignalled. There is deliberately NO per-glob `--reason` pairing:
neither `--add GLOB:REASON` pair syntax nor manual argv-scanning was
built (per instruction). Globs needing genuinely distinct reasons need
separate `frob ticket scope` invocations, one per glob/reason pair --
the "least clever" option (b) from the ticket body.

Fix: a new `_RefuseRepeatedOption` argparse Action (src/frob/
_cli_parsers/_ticket/_metadata.py), applied to both `--reason` and
`--reason-file` on `scope` only (not the single-purpose triage flags on
priority/kind/component/tier, where a repeated flag is an ordinary typo,
not a lost-pairing risk). A second occurrence of either flag now raises
`argparse.ArgumentError`, which argparse turns into a clean `error: ...`
+ exit(2), instead of silently keeping only the last value. Documented
in the flag's own --help text and the parser's docstring.

Historical `scope_changes` entries recorded under the old silent-
collapse behavior (including T-3403's own mis-recorded entries) are
left untouched, per the audit-trail-is-append-only rule -- not
retroactively rewritten.

Committed as two commits, test-first: 7d891e57e (fixtures alone,
against the still-unfixed parser) then 0d9795255 (the fix). Both
must-fire fixtures verified FAILED_AT_PARENT via `frob ticket evidence
--check-repro --base-ref 7d891e57e` -- genuine repros, not confirmatory
-only. Must-stay-quiet fixture (single --add, single --reason) parses
identically to before.

Second, separate finding in the ticket body (doc-anchor scope closure
noise for `--add`ed doc FILES) was explicitly deferred by the ticket to
its own triage, not fixed here.

### Changed
```
 src/frob/_cli_parsers/_ticket/_metadata.py |  71 ++++++++++++++++++-
 tests/test_tickets_scope_mutation.py       | 106 +++++++++++++++++++++++++++++
 tickets/T-3404/ticket.md                   |  20 +++++-
 3 files changed, 193 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_tickets_scope_mutation.py::TestScopeCliRepeatedReasonRefused::test_two_reasons_with_two_adds_is_refused_not_silently_collapsed` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeCliRepeatedReasonRefused::test_two_reason_files_is_also_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeCliRepeatedReasonRefused::test_single_add_single_reason_is_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 15 error(s), 3959 warning(s), 895 waived
- error-findings: CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC006@tickets/T-1382/ticket.md, DOC011@docs/modules/tickets.md, DUP001@src/frob/_cli_parsers/_ticket/_metadata.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3404, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE001@src/frob/_cli_parsers/_ticket/_metadata.py

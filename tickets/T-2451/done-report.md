## Done report

Re-verified this WIRE001 follow_up anchor after T-2746 (which extended
WIRE001 to trace property/attribute access via `_is_property`/
`_PROPERTY_DECORATOR_RE`/`property_access_pattern` in
`src/frob/gates/_wire.py`) -- that extension covers a DIFFERENT gap class
(an `@property`-decorated method read via attribute syntax, no call
parens) and does not touch how the callgraph traces a name passed into a
stdlib registration call like `signal.signal(...)`. This ticket's
disposition is unchanged: (b) genuine callgraph blind spot, not
detector-fixable.

The waiver at `src/frob/process/_reap.py:144` (`frob:waive WIRE001
follow_up="T-2451" reason="genuinely wired -- passed as the handler
argument to signal.signal(...)..."`) already states the actual wiring
mechanism, not just the rule name: `_sigterm_handler` is registered via
`signal.signal(sigterm, _sigterm_handler)` in `install_sigterm_reaper`
(the next function in the same module) and invoked by the interpreter's
own signal-dispatch machinery on a real SIGTERM -- never called directly
by name from Python code, which is exactly the shape `frob.graph.
callgraph`'s best-effort static analysis cannot trace as a caller.

Positive control, both directions, measured directly (not assumed):
1. `frob check --only gates --no-cache` over the whole repo: zero WIRE001
   findings in src/frob/process/_reap.py -- the existing waiver holds.
2. Planted `_t2451_planted_dead_control` (a genuinely dead function, no
   caller anywhere) at the end of src/frob/process/_reap.py, re-ran the
   same check: WIRE001 fired on it immediately
   (`src/frob/process/_reap.py:435 WIRE001: ... is new in this diff and
   has no caller`). Confirms the gate is not blinded on this file --
   removed the plant before landing, tree is clean.

No code change: the waiver and its mechanism-specific reason are already
correct on main. This ticket stays anchor=True/queued forever (T-1856):
WIRE002 requires a real, non-terminal ticket id as follow_up, and closing
this ticket would orphan the citation at _reap.py:144.

Filed: none.

### Changed
```
 tickets/T-2451/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 19 error(s), 833 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, E501@/home/logan/projects/frob/.claude/worktrees/t2766-t2764/src/frob/tickets/_new_renumber.py, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md

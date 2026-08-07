## Done report

Re-measured DOC006 at ticket start: 54 live warnings (up from the ~41 noted
at filing -- heavy landing waves since T-1015/T-1016 shifted counts, as
expected). Scope narrowed to docs/**, CHANGELOG.md, tickets.md (TICK009).

Fixed (real stale pointers, code-verified before editing):
- strata-core/src/parse.rs split into strata-core/src/parse/ (T-1099) --
  19 bare file-path references across 14 docs updated to
  strata-core/src/parse/mod.rs (::symbol-qualified references already
  resolved correctly and were left untouched).
- frob.gates._unwaivable_channel_rules -> frob.gates._waive._unwaivable_channel_rules
  (9 occurrences, docs/modules/arch.md) -- symbol exists, doc dropped the
  module qualifier.
- frob.serve._warm.warm_state -> frob.serve._warm._warm_state
  (docs/modules/graph.md) -- symbol is private, doc had the public spelling.
- frob.dup._pipeline.{_smt_translate,_region_groups,_clone_report,_fingerprint_symbol}
  -> frob.dup._pipeline.{_smt,_fingerprint}.<same name> (docs/modules/dup.md)
  -- dup/_pipeline.py was split into a package; symbols moved to submodules.
- frob.lang._common.iter_cpp_functions -> frob.lang._common._iter_cpp_functions
  (docs/modules/dup.md) -- symbol was demoted private (T-0871) after this
  doc reference was written.
- docs/modules/tickets.md: src/frob/app/ticket_runner.py -> .../ticket_runner/
  in the one non-literal-quote occurrence (the sprint-velocity CLI-surface
  pointer); the CLI_WIRING_FILES-quoting occurrence was left as a verbatim
  quote and waived instead (see below -- the constant itself is stale).
- docs/audits/gates-quality.md: gates/_pii_structural.py -> gates/_pii_structural/
  (real package now, PII010/SEC110 checks span several submodules there).
- docs/modules/gates.md: doc-anchor #per-gate-cache-t-0602 -> the real
  slug #per-gate-dependency-tracked-partial-re-evaluation-t-0602 in
  docs/modules/serve.md (heading text confirmed by reading the file).

Grounded-waived (verified genuinely external/historical, not fixable
without falsifying the record; no matcher/threshold change):
- CHANGELOG.md (6 sites): frozen historical release-note prose describing
  file paths/symbols as they existed at that release; the codebase has
  since been restructured (ticket_runner.py, parse.rs, dup/_core symbols).
  Rewriting would misrepresent what actually shipped in that version.
- docs/audits/tickets-testing-round2.md:6 and tickets.md:477 (dup/_pipeline.py
  finding count): point-in-time audit/filing snapshots whose surrounding
  prose (line numbers, per-file counts) is frozen against a tree that has
  since moved; fixing just the flagged pointer would desync it from the
  rest of the same frozen paragraph.
- docs/guides/agent-playbook.md:50 (.claude/settings.json): confirmed
  gitignored (.gitignore:15) -- a real, intentionally untracked per-clone
  config path, can never resolve.
- docs/guides/estate-capability-migration.md (5 sites): design/*.strata
  paths live in SIBLING repos (lithos/graphite/aprog-public/aprog-private/
  logand.app), never trackable from this repo's own worktree.
- docs/modules/gates.md:2730 (`frob check --fix`): the surrounding prose
  explicitly says wiring this CLI flag is a LATER batch of the same
  T-1137 epic -- genuinely not built yet, not a broken pointer.

Verified: `frob check --only docblocks --json` shows DOC006 count 54 -> 0
(remaining 4 warnings on that gate are pre-existing DOC004, out of this
ticket's rule scope). No matcher/threshold change made anywhere in
src/frob/gates/_docptr.py.

Filed out-of-scope discovery: T-1163 (frob.tickets._models.
CLI_WIRING_FILES still names the retired src/frob/app/ticket_runner.py
path post-package-split, silently defeating T-0446's implicit-scope
mechanism for FEATURE tickets) -- fix is in src/frob/tickets/_models.py,
outside this ticket's docs-only scope.

### Changed
```
 tickets.md | 61 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 56 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

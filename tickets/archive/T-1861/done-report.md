## Done report

Coordinator finding: T-1838 removing ".claude" from BUILTIN_SKIP_DIRS made
`.claude/hooks/**` visible to EVERY graph-reading gate, not just the
WAIVE-edge walk that ticket targeted. Unscoped `frob check` went from
clean to 13 errors (11 new: COV001 across all 5 hook `main`s + 3
`frob-timeout-guard.py` constants + `_shellscan.py`'s `POS`/
`strip_quoted`, plus TEST001 on `strip_quoted`, plus DOC003/THREAT003
CWE-78 on the new `claude_hooks` design node's `may "exec"` -- the last
one discovered only once this ticket ran the FULL unscoped check the
coordinator asked for, not caught by T-1838's own `--only lint` pass).

Fix shape, coordinator-decided:

- COV001 (doc edges, not exemption): these hooks ARE load-bearing -- every
  one executes on every session, `dispatch-telemetry.py` writes real
  telemetry. Added `docs/guides/claude-hooks.md`, one section per hook
  script plus one for the `claude_hooks` design node, and a `frob:doc`
  edge on every flagged symbol (`_shellscan.py::POS`/`strip_quoted`, all 5
  hooks' `main`, `frob-timeout-guard.py`'s `MIN_TIMEOUT_MS`/`PATTERN`/
  `REASON`, `claude_hooks` node). Verified every slug by hand against
  `frob.graph.dsl.slugify`'s exact GitHub-anchor algorithm (strip
  everything outside `[\w\- ]`, lowercase, spaces->hyphens) before
  binding, rather than guessing.

- TEST001 (path-class exemption, not per-file doc/test): `.claude/hooks/
  **` scripts run ONLY under the Claude Code dispatch harness (stdin JSON
  payload, PreToolUse/SessionStart/Stop event dispatch) -- demanding
  pytest unit coverage of them is not real assurance, and becomes a
  waived-forever tax. `_test001_002` (src/frob/gates/__init__.py) already
  has exactly this shape of exemption for `*.strata` files (T-0168); added
  a symmetric `record.id.path.startswith(".claude/hooks/")` clause next
  to it, same function, same precedent. Added a real regression test
  mirroring the existing `test_test001_exempts_strata_flow_declarations`
  test, verified by hand to fail with the exemption clause disabled and
  pass with it restored.

- DOC003/THREAT003 CWE-78 (discharge, not a real gap): `claude_hooks`'s
  `may "exec"` (dispatch-telemetry.py's `_run_git` helper, a fixed
  `["git", "-C", str(root), *args]` argv with `args` always a hardcoded
  literal list) drags in the same CWE-78 obligation `core`/`vet`/
  `tickets_ledger`/`fleet`/`mutate`/`natives`/`deploy` already carry and
  discharge in `design/frob.strata` via `assume "weakness:CWE-78:<node>"
  noflow registry -> <node>`. `registry` (the foreign PyPI/npm/crates.io/
  OSV node) has no flow into `claude_hooks` at all -- it only receives a
  JSON payload from the harness itself -- so the identical `noflow`
  discharge applies; added it following the exact precedent shape.

Verified: `frob check --budget 500 --ticket T-1861` (31-43 gate
families run across two passes) shows every substantive gate family
`pass`; the only FAIL is `gate:PRE` (PRE001, the "no active ticket
derivable" branch-detection artifact of running without a T-####-name
branch, pre-existing and unrelated). `frob check --only gates-fast` and
`--only gates-security` both individually confirm `gate:COV`/`gate:TEST`/
`gate:DOC`/`gate:SEC` all pass 0 errors.

### Changed
```
 tickets/T-1861/ticket.md | 77 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 77 insertions(+)
```

### Evidence
- `tests/test_gates.py::TestConventionUnitBinding::test_test001_exempts_claude_hooks_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 1355 warning(s), 742 waived
- error-findings: PRE001@tickets/T-1861

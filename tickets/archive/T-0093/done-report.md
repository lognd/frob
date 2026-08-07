## Done report

Changed:
strata-core/src/parse/mod.rs::Parser::parse_queue
strata-core/src/parse/mod.rs::Parser::parse_balancer
src/frob/strata/_ast.py::QueueDecl
src/frob/strata/_ast.py::BalancerDecl
src/frob/strata/_infra.py::_elaborate_queue
src/frob/strata/_infra.py::_elaborate_balancer
docs/strata/surface.md#std-infra (grammar block, desugar table, deviation note)

Grammar added: `queue ID (":" TRUST)? "{" ... "}"?` and
`balancer ID (":" TRUST)? "{" ... "}"?` -- optional TRUST clause, matching
store/cache/cdn's shape. Rust parser emits `"trust": null` when omitted
(new field on the queue/balancer JSON payload); `QueueDecl.trust` /
`BalancerDecl.trust` are `str | None = None` on the pydantic side (no
python-side JSON translation needed -- `Module.model_validate` picks the
new field up directly). `_elaborate_queue`/`_elaborate_balancer` now use
`decl.trust or _INFRA_DEFAULT_TRUST`, only logging the WARNING default
message when `decl.trust is None`. Fully backward-compatible: the clause
is optional, so every pre-existing `.strata` source (including all four
design/litmus/*.strata goldens, none of which declare queue/balancer
trust) parses and elaborates identically.

Evidence:
tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_no_trust_clause_defaults_to_trusted
tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_explicit_trust_clause_wins_over_default
tests/unit/strata/test_infra.py::TestBalancerDesugar::test_balancer_explicit_trust_clause_wins_over_default
(also added, not yet resolvable as ticket evidence -- rust runner has no
[[test.runner]] entry, T-0092 libpython gap -- but present and reviewable
in strata-core/src/parse/mod.rs::tests: parses_queue_with_explicit_trust,
parses_queue_without_trust_defaults_to_null, parses_bare_queue_with_trust,
parses_balancer_with_explicit_trust, parses_bare_balancer_with_trust, and
the trust=None assertion added to parses_bare_balancer)

Test/check numbers:
- tests/unit/strata: 242 passed, 0 failed (baseline before this ticket's
  edits: 239 collected/passed on old main; post-merge-to-7041eac baseline
  before my edits was already 239 -> 242 after adding 3 python tests to
  test_infra.py; test_infra.py alone went 20 -> 24 collected, +4 counting
  one pre-existing balancer assertion extended in place)
- cargo test --manifest-path strata-core/Cargo.toml: NOT RUNNABLE in this
  environment (pyo3-build-config fails: "cannot set a minimum Python
  version 3.11 higher than the interpreter version 3.10" -- the T-0092
  libpython gap noted in the dispatch instructions). New rust unit tests
  added to strata-core/src/parse.rs follow the existing `ok(...)`/`err(...)`
  harness style and are believed correct by inspection but not locally
  executed.
- design/litmus/*.strata goldens: all 4 (chirp/payments/payments_hardened/
  tube) still pass via tests/unit/strata/test_litmus_*.py -- none declare
  queue/balancer trust, confirming backward compatibility.
- `frob check` (no --ticket): exit 1 driven solely by 2 pre-existing
  ruff-format findings on src/frob/strata/_breach.py and
  tests/unit/strata/test_breach.py (from the main merge, files I never
  touched). Gates-stage diagnostic count: 97 both before and after my
  edits (identical diagnostics, only line numbers shifted from my added
  docstrings) -- confirmed by diffing gates JSON with my changes
  stashed vs. applied. One E501 (line too long) I introduced in
  _infra.py was caught and fixed before this comparison.
- `frob check --ticket T-0093`: after fixing tickets.md's scope field
  (see below) and re-running `frob ticket sweep T-0093`, gates diagnostics
  are exactly: 1x SCOPE001 on tickets.md (expected ledger-tracking
  self-flag per prior ticket precedent, e.g. T-0046's Done report) + 6x
  COV003 on tickets/T-0106 (pre-existing, unrelated to T-0093, filed as
  T-0125) + pre-existing TEST002/TEST003/PERF003/PERF004 noise already
  present repo-wide. No SCOPE001 on any file I actually touched.
- `frob test --base main`: python touched-set selection
  (src/frob/strata, tests/unit/strata/test_infra.py) exits 0. Rust
  touched-set selection (strata-core/src) fails with NoRunner -- no
  [[test.runner]] for language "rust" in frob.toml, same T-0092 gap as
  cargo test above.

tickets.md mechanics fix: T-0093's `scope:` field was recorded as a
single YAML list item containing a comma-joined path string
(`- strata-core/src/parse.rs,src/frob/strata/_ast.py,...`) instead of one
glob per list item, which made every file I actually touched trip
SCOPE001. Split it into one entry per path and added
`tests/unit/strata/test_infra.py` (the test file the ticket's own scope
description requires touching) that was missing from the original scope
list. Re-ran `frob ticket sweep T-0093` after the scope edit per PRE001's
instruction.

Filed: T-0125 (T-0106 evidence ids do not resolve to collected tests,
COV003 -- pre-existing, unrelated to T-0093)

Gates: `frob check --ticket T-0093` clean except the tickets.md
self-flag (expected, documented ledger-tracking pattern) and the T-0125
pre-existing COV003 findings on another ticket's evidence (filed, not
fixed, out of scope). No new SCOPE001/PERF/TEST findings on any file this
ticket touched. Rust side unverified by `cargo test` due to the
pre-existing T-0092 libpython/abi3 build gap -- not something introducable
or fixable within T-0093's scope.

NOT closed, NOT committed per dispatch instructions.

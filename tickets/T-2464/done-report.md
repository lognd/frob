## Done report

Changed:
  src/frob/vet/_capability_registry/_kinds.py -- new capability_kind
    "net-mutate", registered with an explicit "unwired, scanner-only"
    docstring note (same posture as the pre-existing "proc"/"ffi"
    precedent).
  src/frob/vet/_capability_registry/_dangerous_ops_python.py -- 2 new
    `_op` entries: requests.post/put/delete/patch and httpx.post/put/
    delete/patch (module-level convenience calls only), both kind
    "net-mutate", ADDITIVE to the existing coarse requests./httpx.
    needles (unchanged).
  src/frob/vet/_capability_registry/_matrix.py -- 4 `_MatrixExcuse`
    entries (typescript/rust/c-cpp/kotlin) disclosing net-mutate as a
    python-only pass, not silently absent.
  src/frob/strata/_selfconform.py -- `_EXTENDED_KINDS` gains net-mutate
    (SYS100's drift-lock test requires every `_PATTERNS`-defined kind be
    accounted for in either `_KIND_MAP` or here; net-mutate has no
    tier-2 join by design, so it goes here).
  src/frob/strata/_threat_catalog_benign.py -- a `BenignCapability`
    excuse for net-mutate's raw hyphenated spelling (THREAT002's own
    obligation check requires SOME catalog disposition for a kind that
    is actually DECLARED via `may`; net-mutate is the FIRST capability
    in this registry ever declared via its raw scanner-kind spelling
    directly rather than a bare-family or wired dotted spelling -- see
    the entry's own comment for why, and the explicit disclosure that
    "benign" here means "no CWE mapping exists yet", not a security
    judgment that mutating network calls are actually safe).
  design/frob.strata -- `may "net-mutate" via "tests/test_capability_
    registry.py";` on the testsuite node (my own new test fixtures'
    literal needle text is real, scanned code, same self-conformance
    precedent every other fixture-literal declaration on this node
    already follows).
  docs/modules/vet.md -- CAPABILITY_KINDS paragraph updated (~25 -> ~26
    entries, net-mutate named with its unwired/scoped caveats).
  tests/test_capability_registry.py -- new `TestNetMutateVerbSplit`
    class, 5 tests covering all 4 of this ticket's acceptance criteria.

Evidence:
  tests/test_capability_registry.py::TestNetMutateVerbSplit::test_requests_post_reports_net_mutate_and_net_connect  (accepts 0)
  tests/test_capability_registry.py::TestNetMutateVerbSplit::test_httpx_delete_reports_net_mutate  (accepts 0)
  tests/test_capability_registry.py::TestNetMutateVerbSplit::test_requests_get_only_does_not_report_net_mutate  (accepts 1)
  tests/test_capability_registry.py::TestNetMutateVerbSplit::test_httpx_get_only_does_not_report_net_mutate  (accepts 1)
  tests/test_capability_registry.py::TestNetMutateVerbSplit::test_session_instance_method_gap_is_unchanged  (accepts 2, 3)
  `tests/test_capability_registry.py`: 433 collected, 0 failed.
  `tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock`:
  3 collected, 0 failed.

DESIGN DECISION (the ticket's own "needs its own design decision on
whether a verb-aware split is even tractable" instruction): scoped to
the two libraries with an unambiguous, flat-needle-visible verb split
(requests./httpx. module-level convenience functions) as an ADDITIVE
scanner-only signal, deliberately NOT wired into `_capability_modes.py`'s
FAMILY_MODES/WIRED_MODE_FAMILIES (no `may "net"` conformance join reads
it yet) -- same incremental "vocabulary defined, tier-2 join deferred"
posture this repo already used for `proc`/`ffi` (T-0771's own precedent,
documented in `_capability_modes.py`'s own "Wiring status" section).
Chose ADDITIVE over REPLACING the coarse net-connect needle specifically
so this is a strict precision GAIN with zero recall risk on the existing
signal (acceptance [2]'s own control).

NOT covered, disclosed rather than silently dropped (acceptance [3]):
  - aiohttp: real usage is `session.post(url)` (ClientSession instance
    method), not a module-level call -- a bare `.post(`/`.put(` needle
    with no library prefix would false-positive on any object's
    unrelated same-named method. Same underlying gap requests/httpx also
    have for their OWN instance-method form (`Session().post(...)`) --
    not aiohttp-specific.
  - boto3: HIGHEST VALUE, HARDEST TO COVER -- per-service verb methods
    (`put_object`/`create_bucket`/`create_user`/...) with no flat-needle
    shape; needs the binding-resolver extension T-2469's follow-up
    describes, not a needle-table entry. Explicitly recommended AGAINST
    a quick needle-table attempt in the follow-up ticket's own body.
  - asyncpg: `.execute(`/`.fetch(` split cleanly by method name, but the
    underlying SQL string's actual read/write shape is the same
    inherent ambiguity the existing `sql` capability kind (sqlite3/
    sqlalchemy) already carries -- not a new gap this ticket introduces.
  - http.client/ftplib/smtplib/socket: no clean verb-shaped convenience-
    function idiom; smtplib specifically may deserve reclassifying its
    OWN entry to net-mutate outright (sending mail has no read-only
    mode) rather than splitting it -- a judgment call left to the
    follow-up, not decided here.
  Filed as T-2479 (renumbers at land) -- boto3/aiohttp/asyncpg
  mutating-verb split not covered by this ticket's net-mutate signal,
  with a concrete recommendation (extend the existing T-0328 binding
  resolver for boto3, not a flat needle) so the next agent does not
  waste a pass discovering that a needle-table fix does not hold up.

Gates: `frob check --only lint --ticket T-2464` -- 0 errors/warnings on
every file this ticket touched. `frob check --only gates-security
--ticket T-2464` -- before this ticket's fix, 2 new errors appeared
(DOC003 THREAT002 obligation failure for the undeclared net-mutate
kind, SELFAUDIT001 SYS111 ratchet ceiling); DOC003 fixed via the
BenignCapability excuse above (confirmed gone in a re-run); the SYS111
ratchet ceiling is the SAME class T-2466's own land absorbed via its
Tier-A auto-fix handler (`fix_sys111_capability_ratchet_sync`) and is
expected to self-resolve at land, not a blocker. Every OTHER error
present in both runs (stratamod/core SYS100, checker/fleet/deploy/vet
SYS101, SEC110, WIRE003, GATERULE001, DRIFT002) is pre-existing baseline
noise, confirmed unrelated by cross-referencing T-2457/T-2466's own
recent land warnings which show the identical findings.

### Changed
```
 tickets/T-2464/ticket.md           | 67 ++++++++++++++++++++++++++++++-
 tickets/T-2479/ticket.md | 81 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 147 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_capability_registry.py::TestNetMutateVerbSplit::test_requests_post_reports_net_mutate_and_net_connect` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestNetMutateVerbSplit::test_httpx_delete_reports_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestNetMutateVerbSplit::test_requests_get_only_does_not_report_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestNetMutateVerbSplit::test_httpx_get_only_does_not_report_net_mutate` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestNetMutateVerbSplit::test_session_instance_method_gap_is_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2464/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2464/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2464/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2464/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2464/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2464, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py

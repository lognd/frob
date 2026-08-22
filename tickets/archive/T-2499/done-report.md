## Done report

_capability_test_discovery_status hardcoded {python, rust, typescript,
c, cpp} -- the identical pattern T-2494 already fixed for
_capability_import_graph_status -- and it was already stale the day it
would matter: T-2409 landed a real frob.testing.collect_kotlin_tests
collector today, and this hardcoded set had no way to know about it.

Unlike _IMPORT_WALKERS (frob.lang._extract), frob.testing has no
existing language-keyed dispatch table joining its five collect_*_tests
functions -- confirmed by search, no caller in this repo dispatches a
collector by language string. So there was no existing single source of
truth to import and derive from; building that registry was the real
deliverable, per the ticket's own caveat.

Added _TEST_DISCOVERY_COLLECTORS: dict[str, str] in _support.py, mapping
language -> frob.testing qualname. _capability_test_discovery_status now
derives IMPLEMENTED/KNOWN_GAP from this dict's keys, with the named
attribute resolved LIVE against frob.testing (getattr) rather than
trusted as a string alone -- a renamed/removed collector reports
KNOWN_GAP with an explicit "registry entry is stale" detail, not a dead
IMPLEMENTED. Removed the now-stale T-2409 entry from
KNOWN_GAP_TRACKING_TICKETS since no detail string cites it any more.

Also fixed AFFECT001 (touched docs/modules/lang.md's test_discovery
bullet) and waived OPAQUE001 (the dynamic getattr is deliberate -- a
static literal would defeat the exact staleness check this function
exists to run).

### Changed
```
 docs/modules/lang.md       | 21 +++++++---
 src/frob/lang/_support.py  | 99 +++++++++++++++++++++++++++++++++++++++-------
 tests/test_lang_support.py | 50 +++++++++++++++++++++++
 tickets/T-2499/ticket.md   | 29 +++++++++++++-
 4 files changed, 177 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_kotlin_test_discovery_is_implemented` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_test_discovery_known_gap_tracks_a_language_absent_from_registry` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_test_discovery_known_gap_when_registry_entry_is_stale` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2499/src/frob/testing/_collect_kotlin.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2499/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
